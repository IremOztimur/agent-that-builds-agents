"""Policy code that runs inside the workflow, as source strings (code nodes and the controller tool).

Trust boundary: only the nodes in WRITERS may write trusted state. The controller tool the model calls
writes candidates (cand_*) and the line to say, never trusted state. Every snippet:
- reads from `vars` (and `params` in the controller), never from {{ }} placeholders;
- never raises: on any error it fails closed;
- contains no double braces (config comes in as a literal through nodes.literal).
"""
from nodes import literal

TRUSTED_PREFIXES = ("auth_", "idok_", "id_state", "acct_used")
WRITERS = ("after_verify", "gate_account", "after_account")


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


# --- after_account: consumes the authorisation first, then turns the bank's answer into the line to say -----------
AFTER_ACCOUNT = r'''
import json
CFG = __CFG__
vars['auth_account'] = 'used'
vars['acct_used'] = 'yes'
try:
    ok = str(vars.get('acct_ok') or '').strip().lower() == 'true'
    products = json.loads(str(vars.get('products_json') or '[]')) if ok else []
    parts = []
    for p in products:
        words = CFG['product_words'].get(str(p.get('type')), CFG['product_default'])
        words = words.replace('CARD_LAST4', str(p.get('card_last4') or ''))
        line = CFG['line']
        line = line.replace('WORDS', words)
        line = line.replace('PAST_DUE', format(float(p.get('past_due')), '.2f'))
        line = line.replace('DAYS_LATE', str(int(float(p.get('days_late')))))
        parts.append(line)
    if parts:
        vars['debt_line'] = ' '.join(parts)
        vars['acct_state'] = 'ok'
    else:
        vars['acct_state'] = 'error'
except Exception:
    vars['acct_state'] = 'error'
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


def after_account(cfg):
    return _inject(AFTER_ACCOUNT, cfg)
