"""Policy code that runs inside the workflow, as source strings (code nodes and the controller tool).

Trust boundary: only the nodes in WRITERS may write trusted state. The controller tool the model calls
writes candidates (cand_*) and the line to say, never trusted state. Every snippet:
- reads from `vars` (and `params` in the controller), never from {{ }} placeholders;
- never raises: on any error it fails closed;
- contains no double braces (config comes in as a literal through nodes.literal).
"""
from nodes import literal

TRUSTED_PREFIXES = ("auth_", "idok_", "id_state", "acct_used", "facts_", "promise_")
WRITERS = ("after_verify", "gate_account", "after_account", "gate_promise", "after_promise")


def _inject(template, cfg):
    return template.replace("__CFG__", literal(cfg))


# --- controller: the model reports a candidate answer; code validates it and decides the move -----------------
CONTROLLER = r'''
import re, datetime
CFG = __CFG__
try:
    p = params if isinstance(params, dict) else dict()
    questions = CFG['questions']
    pending = ''
    for q in questions:
        if str(vars.get('idok_' + q['field']) or '') != 'yes':
            pending = q['field']
            break
    for k in ('vf_ok', 'vf_verified', 'vf_all', 'vf_left', 'vf_hint', 'vf_error'):
        vars[k] = ''
    vars['go'] = ''
    field = str(p.get('field') or '').strip()
    raw = str(p.get('answer') or '').strip()
    q = None
    for x in questions:
        if x['field'] == pending:
            q = x
    cleaned = ''
    if q is not None and field == pending:
        if q['kind'] == 'date':
            m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', raw)
            if m:
                try:
                    datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    cleaned = raw
                except Exception:
                    cleaned = ''
        elif q['kind'] == 'digits4':
            d = re.sub(r'[^0-9]', '', raw)
            if len(d) == 4:
                cleaned = d
    if q is None:
        vars['say'] = CFG['fallback']
    elif field != pending:
        vars['say'] = q['ask']
    elif not cleaned:
        vars['say'] = q['retry']
    else:
        vars['cand_field'] = field
        vars['cand_answer'] = cleaned
        vars['go'] = 'verify'
        vars['say'] = ''
except Exception:
    vars['go'] = ''
    vars['say'] = CFG['fallback']
'''


# --- after_verify: reads the bank's own answer and is the only writer of verification state ---------------------
AFTER_VERIFY = r'''
CFG = __CFG__
try:
    def low(k):
        v = vars.get(k)
        return '' if v is None else str(v).strip().lower()
    field = str(vars.get('cand_field') or '')
    vars['go'] = ''
    got = low('vf_ok') in ('true', 'false')
    ok = low('vf_ok') == 'true'
    verified = low('vf_verified') == 'true'
    all_ok = low('vf_all') == 'true'
    try:
        left = int(float(vars.get('vf_left')))
    except Exception:
        left = None
    hint = low('vf_hint')
    questions = CFG['questions']
    by_field = dict((q['field'], q) for q in questions)
    q = by_field.get(field)
    try:
        unread = int(float(vars.get('vf_unread') or 0))
    except Exception:
        unread = 0
    vars['id_state'] = str(vars.get('id_state') or 'open')
    if q is None:
        vars['id_state'] = 'failed'
    elif not got:
        unread += 1
        vars['vf_unread'] = unread
        vars['say'] = q['retry']
        if unread >= CFG['max_unread']:
            vars['id_state'] = 'failed'
    else:
        vars['vf_unread'] = 0
        if hint == 'day_month_swapped':
            vars['say'] = CFG['swapped']
        elif not ok:
            vars['say'] = q['retry']
        elif verified:
            vars['idok_' + field] = 'yes'
            done = True
            for x in questions:
                if str(vars.get('idok_' + x['field']) or '') != 'yes':
                    done = False
                    vars['say'] = CFG['next_prefix'] + x['ask']
                    break
            if done and all_ok:
                vars['id_state'] = 'passed'
            elif done:
                vars['id_state'] = 'failed'
        elif left is not None and left <= 0:
            vars['id_state'] = 'failed'
        else:
            vars['say'] = CFG['wrong_prefix'] + q['ask']
except Exception:
    vars['id_state'] = 'failed'
'''


# --- gate_account: the only place a protected read is authorised; fails closed -------------------------------------
GATE_ACCOUNT = r'''
CFG = __CFG__
try:
    ok = str(vars.get('id_state') or '') == 'passed'
    for f in CFG['fields']:
        if str(vars.get('idok_' + f) or '') != 'yes':
            ok = False
    if str(vars.get('acct_used') or '') == 'yes':
        ok = False
    vars['auth_account'] = 'granted' if ok else 'denied'
except Exception:
    vars['auth_account'] = 'denied'
'''


# --- shared calendar and validation helpers (inlined into every snippet that needs them) --------------------------
CAL = r'''
import datetime, json
HOL = set(CFG['holidays'])
ONE = datetime.timedelta(days=1)
def isbiz(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def nextbiz(d):
    d = d + ONE
    while not isbiz(d):
        d = d + ONE
    return d
def nthbiz(d, n):
    for i in range(n):
        d = nextbiz(d)
    return d
def words(d):
    return d.strftime('%A') + ' ' + str(d.day) + ' ' + d.strftime('%B')
def money(x):
    return format(float(x), '.2f')
def pick(facts, pid):
    for f in facts:
        if str(f.get('product_id')) == str(pid):
            return f
    return None
def check(fact, amount, date_iso, today):
    """Returns (code, detail). code is 'ok' or the reason the proposal cannot be recorded."""
    try:
        d = datetime.date.fromisoformat(str(date_iso)[:10])
    except Exception:
        return ('bad_input', '')
    try:
        a = round(float(amount), 2)
    except Exception:
        return ('bad_input', '')
    dl = datetime.date.fromisoformat(fact['deadline']) if fact.get('deadline') else None
    if dl is None or not fact.get('valid'):
        return ('blocked', '')
    if a > float(fact['full']) + 0.005:
        return ('too_much', '')
    if a < float(fact['floor']) - 0.005:
        return ('too_little', '')
    if d < today:
        return ('past', '')
    if d > dl:
        return ('late', '')
    if d.isoformat() not in fact['valid']:
        n = nextbiz(d)
        return ('nonbiz', n.isoformat() if n <= dl else dl.isoformat())
    return ('ok', '')
'''


PROP = r'''
def turn_now():
    try:
        return int(float(vars.get(CFG['turn_key'])))
    except Exception:
        return None
def store(fact, amount, date_iso, turn):
    d = datetime.date.fromisoformat(str(date_iso)[:10])
    seq = int(float(vars.get('prop_seq') or 0)) + 1
    vars['prop_seq'] = seq
    vars['prop_id'] = 'prop' + str(seq)
    vars['prop_product'] = fact['product_id']
    vars['prop_amount'] = round(float(amount), 2)
    vars['prop_date'] = d.isoformat()
    vars['prop_turn'] = turn if turn is not None else 999999
    vars['prop_state'] = 'readback'
    vars['conf_state'] = ''
    vars['conf_for'] = ''
    vars['offer_state'] = ''
    vars['say'] = CFG['lines']['readback'].replace('AMOUNT', money(amount)).replace('PRODUCT', fact['words']).replace('DATE', words(d))
def clear_offer():
    vars['offer_state'] = ''
def set_offer(fact, amount, date_iso, turn):
    vars['offer_state'] = 'open'
    vars['offer_product'] = fact['product_id']
    vars['offer_amount'] = round(float(amount), 2)
    vars['offer_date'] = str(date_iso)[:10]
    vars['offer_turn'] = turn if turn is not None else 999999
'''

# --- after_account: consumes the authorisation, then computes finished facts (limits, calendar) for this customer --
AFTER_ACCOUNT = r'''
CFG = __CFG__
vars['auth_account'] = 'used'
vars['acct_used'] = 'yes'
__CAL__
try:
    ok = str(vars.get('acct_ok') or '').strip().lower() == 'true'
    products = json.loads(str(vars.get('products_json') or '[]')) if ok else []
    now = datetime.datetime.fromisoformat(str(vars.get('now'))[:16])
    today = now.date()
    facts = []
    parts = []
    for p in products:
        typ = str(p.get('type'))
        words_ = CFG['product_words'].get(typ, CFG['product_default']).replace('CARD_LAST4', str(p.get('card_last4') or ''))
        full = round(float(p.get('past_due')), 2)
        days = int(float(p.get('days_late')))
        floor = round(float(p.get(CFG['floor_fields'][typ])), 2) if typ in CFG['floor_fields'] and p.get(CFG['floor_fields'][typ]) is not None else None
        band = None
        for b in CFG['bands']:
            if b['min_days'] <= days <= b['max_days']:
                band = b
        fact = dict(product_id=str(p.get('product_id')), type=typ, words=words_, full=full, floor=floor, days=days, deadline='', valid=[])
        if band is not None and floor is not None:
            dl = nthbiz(today, int(band['deadline_bd']))
            valid = []
            d = today
            while d <= dl:
                if isbiz(d):
                    valid.append(d.isoformat())
                d = d + ONE
            fact['deadline'] = dl.isoformat()
            fact['valid'] = valid
        facts.append(fact)
        line = CFG['line'].replace('WORDS', words_).replace('PAST_DUE', money(full)).replace('DAYS_LATE', str(days))
        parts.append(line)
    if facts and all(f['valid'] for f in facts):
        f0 = facts[0]
        dl0 = datetime.date.fromisoformat(f0['deadline'])
        mon = today - datetime.timedelta(days=today.weekday())
        names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        wk = []
        for i in range(7):
            a = mon + datetime.timedelta(days=i)
            wk.append('this ' + names[i] + ' = ' + a.isoformat() + ', next ' + names[i] + ' = ' + (a + datetime.timedelta(days=7)).isoformat())
        wk.append('tomorrow = ' + (today + ONE).isoformat())
        vars['facts_json'] = json.dumps(facts)
        vars['today_iso'] = today.isoformat()
        vars['product_name'] = f0['words']
        vars['full_amt'] = money(f0['full'])
        vars['floor_amt'] = money(f0['floor'])
        vars['floor_name'] = CFG['floor_names'].get(f0['type'], 'lowest amount')
        vars['deadline_words'] = words(dl0)
        vars['weekday_table'] = chr(10).join(wk)
        vars['debt_line'] = ' '.join(parts) + ' ' + CFG['first_ask']
        vars['acct_state'] = 'ok'
    else:
        vars['acct_state'] = 'error'
except Exception:
    vars['acct_state'] = 'error'
'''

# --- controller tools of the negotiation: the model reports, code validates and decides --------------------------
PROPOSAL = r'''
CFG = __CFG__
__CAL__
__PROP__
try:
    p = params if isinstance(params, dict) else dict()
    vars['go'] = ''
    L = CFG['lines']
    facts = json.loads(str(vars.get('facts_json') or '[]'))
    fact = pick(facts, p.get('product_id')) if p.get('product_id') else (facts[0] if len(facts) == 1 else None)
    today = datetime.date.fromisoformat(str(vars.get('today_iso')))
    turn = turn_now()
    if fact is None:
        vars['say'] = L['bad_input']
    else:
        code, detail = check(fact, p.get('amount'), p.get('date'), today)
        try:
            d_new = datetime.date.fromisoformat(str(p.get('date'))[:10]).isoformat()
        except Exception:
            d_new = ''
        try:
            amt = round(float(p.get('amount')), 2)
        except Exception:
            amt = None
        same = (code == 'ok' and str(vars.get('prop_state') or '') == 'readback' and str(vars.get('prop_product')) == fact['product_id']
                and abs(float(vars.get('prop_amount') or 0) - amt) < 0.005 and str(vars.get('prop_date')) == d_new)
        if same:
            # the identical proposal again: nothing changes, so the read-back and its confirmation clock stay as they were
            vars['say'] = CFG['lines']['readback'].replace('AMOUNT', money(amt)).replace('PRODUCT', fact['words']).replace('DATE', words(datetime.date.fromisoformat(d_new)))
        elif code == 'ok':
            store(fact, amt, d_new, turn)
        else:
            vars['prop_state'] = ''
            vars['conf_state'] = ''
            vars['conf_for'] = ''
            clear_offer()
            dl = datetime.date.fromisoformat(fact['deadline']) if fact.get('deadline') else today
            nxt = datetime.date.fromisoformat(detail) if code == 'nonbiz' and detail else today
            # the code, not the model, remembers what it offered: a later yes accepts exactly this
            if code in ('late', 'nonbiz') and amt is not None:
                set_offer(fact, amt, (dl.isoformat() if code == 'late' else nxt.isoformat()), turn)
            elif code in ('too_little', 'too_much') and d_new and d_new in fact['valid']:
                set_offer(fact, (fact['floor'] if code == 'too_little' else fact['full']), d_new, turn)
            try:
                shown = words(datetime.date.fromisoformat(d_new))
            except Exception:
                shown = 'That date'
            vars['say'] = L.get(code, L['bad_input']).replace('DEADLINE', words(dl)).replace('NEXT', words(nxt)).replace('SHOWN', shown).replace('FLOOR', money(fact['floor'] or 0)).replace('FULL', money(fact['full']))
except Exception:
    vars['go'] = ''
    vars['prop_state'] = ''
    vars['say'] = CFG['lines']['bad_input']
'''

CONFIRMATION = r'''
CFG = __CFG__
__CAL__
__PROP__
try:
    p = params if isinstance(params, dict) else dict()
    vars['go'] = ''
    L = CFG['lines']
    decision = str(p.get('decision') or '').strip().lower()
    turn = turn_now()
    try:
        prop_turn = int(float(vars.get('prop_turn')))
    except Exception:
        prop_turn = 999999
    if str(vars.get('prop_state') or '') == 'readback':
        if turn is None or turn <= prop_turn:
            vars['say'] = L['wait_reply']
        elif decision == 'yes':
            vars['conf_state'] = 'yes'
            vars['conf_for'] = str(vars.get('prop_id') or '')
            vars['go'] = 'promise'
            vars['say'] = ''
        else:
            vars['prop_state'] = ''
            vars['conf_state'] = ''
            vars['conf_for'] = ''
            vars['say'] = L['declined']
    elif str(vars.get('offer_state') or '') == 'open':
        # no read-back is open, but the code made an offer: a yes on a later turn accepts that offer and starts the read-back
        try:
            offer_turn = int(float(vars.get('offer_turn')))
        except Exception:
            offer_turn = 999999
        if turn is None or turn <= offer_turn:
            vars['say'] = L['need_proposal']
        elif decision == 'yes':
            facts = json.loads(str(vars.get('facts_json') or '[]'))
            fact = pick(facts, vars.get('offer_product'))
            today = datetime.date.fromisoformat(str(vars.get('today_iso')))
            code, detail = ('bad_input', '') if fact is None else check(fact, vars.get('offer_amount'), vars.get('offer_date'), today)
            if code == 'ok':
                store(fact, vars.get('offer_amount'), vars.get('offer_date'), turn)
            else:
                clear_offer()
                vars['say'] = L['need_proposal']
        else:
            clear_offer()
            vars['say'] = L['declined']
    else:
        vars['say'] = L['need_proposal']
except Exception:
    vars['go'] = ''
    vars['say'] = CFG['lines']['need_proposal']
'''

# --- gate_promise: the only place a write is authorised; re-validates everything from trusted state ---------------
GATE_PROMISE = r'''
CFG = __CFG__
__CAL__
try:
    ok = str(vars.get('id_state') or '') == 'passed'
    for f in CFG['fields']:
        if str(vars.get('idok_' + f) or '') != 'yes':
            ok = False
    facts = json.loads(str(vars.get('facts_json') or '[]'))
    fact = pick(facts, vars.get('prop_product'))
    today = datetime.date.fromisoformat(str(vars.get('today_iso')))
    if fact is None:
        ok = False
    else:
        code, detail = check(fact, vars.get('prop_amount'), vars.get('prop_date'), today)
        if code != 'ok':
            ok = False
    if str(vars.get('prop_state') or '') != 'readback' or str(vars.get('conf_state') or '') != 'yes':
        ok = False
    if not str(vars.get('prop_id') or '') or str(vars.get('conf_for') or '') != str(vars.get('prop_id') or ''):
        ok = False
    try:
        attempts = int(float(vars.get('promise_attempts') or 0))
    except Exception:
        attempts = 99
    if attempts >= CFG['max_attempts']:
        ok = False
    if str(vars.get('promise_state') or '') == 'recorded':
        ok = False
    vars['pr_ok'] = ''
    vars['pr_id'] = ''
    vars['auth_promise'] = 'granted' if ok else 'denied'
except Exception:
    vars['auth_promise'] = 'denied'
'''

# --- after_promise: consumes the authorisation; only the bank's answer can make a promise recorded ---------------
AFTER_PROMISE = r'''
CFG = __CFG__
vars['auth_promise'] = 'used'
try:
    try:
        attempts = int(float(vars.get('promise_attempts') or 0)) + 1
    except Exception:
        attempts = 99
    vars['promise_attempts'] = attempts
    ok = str(vars.get('pr_ok') or '').strip().lower() == 'true' and str(vars.get('pr_id') or '').strip() != ''
    if ok:
        vars['promise_state'] = 'recorded'
    elif attempts < CFG['max_attempts']:
        vars['promise_state'] = 'retry'
    else:
        vars['promise_state'] = 'failed'
except Exception:
    vars['promise_state'] = 'failed'
'''

# --- post hook on the account read: hands the product list on as one string ----------------------------------------
POST_ACCOUNT = r'''
try:
    import json
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if isinstance(d, dict) and isinstance(d.get('products'), list):
            d['products_json'] = json.dumps(d.get('products'))
except Exception:
    pass
'''


def controller(cfg):
    return _inject(CONTROLLER, cfg)


def after_verify(cfg):
    return _inject(AFTER_VERIFY, cfg)


def gate_account(cfg):
    return _inject(GATE_ACCOUNT, cfg)


def _snippet(template, cfg):
    return _inject(template.replace("__CAL__", CAL).replace("__PROP__", PROP), cfg)


def after_account(cfg):
    return _snippet(AFTER_ACCOUNT, cfg)


def proposal(cfg):
    return _snippet(PROPOSAL, cfg)


def confirmation(cfg):
    return _snippet(CONFIRMATION, cfg)


def gate_promise(cfg):
    return _snippet(GATE_PROMISE, cfg)


def after_promise(cfg):
    return _inject(AFTER_PROMISE, cfg)
