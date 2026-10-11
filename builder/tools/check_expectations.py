"""Check expectations.json: what each practice topic must leave in the bank and say on the call, derived from rules.json.

    python3 tools/check_expectations.py [expectations.json] [rules.json] [topics.json]

Per topic id: what the bank must show: {"outcome", "reason", "promises": [...], "notes": [...], "callbacks": [...], "transfers": [...]} (the practice bank) or
{"calls": [{"tool", "args": {the arguments that matter}}], "forbidden_calls": [tool names], "state": {...}} (a mock), plus
"must_state": ["words or facts the agent has to say"], "must_not": ["what it must not say or do"], "rules": ["r1", ...].
Fails when a topic has no entry, an entry has no outcome, cites no live rule or cites an unknown one.
"""
import json, sys

LIVE = ("decided", "proposed", "unresolved")
REQUIRED_LISTS = ("must_state", "must_not", "rules")
OPTIONAL_LISTS = ("promises", "notes", "callbacks", "transfers", "calls", "forbidden_calls")


def problems(exp, rules, topics, final=False):
    live = {r["id"] for r in rules if r.get("status") in LIVE}
    known = {r["id"] for r in rules}
    bad = []
    for t in topics:
        if final:
            if not t.get("script"):
                bad.append("%s: a topic needs a script, what this customer does on the call" % t["id"])
            if not isinstance(t.get("variables"), dict) or not t["variables"]:
                bad.append("%s: a topic needs variables, the values the call starts with (customer id and anything the workflow reads)" % t["id"])
        e = exp.get(t["id"])
        if not isinstance(e, dict):
            bad.append("%s: no entry in expectations.json" % t["id"])
            continue
        if not (e.get("outcome") or e.get("calls") or e.get("state") or e.get("forbidden_calls")):
            bad.append("%s: say what the bank must show: an outcome, the calls it must have received (calls), the state it must end in (state), or calls that must not happen (forbidden_calls)" % t["id"])
        for k in REQUIRED_LISTS:
            if not isinstance(e.get(k), list):
                bad.append("%s: %s must be a list (empty is fine)" % (t["id"], k))
        for k in OPTIONAL_LISTS:
            if k in e and not isinstance(e[k], list):
                bad.append("%s: %s must be a list" % (t["id"], k))
        for c in e.get("calls") or []:
            if not (isinstance(c, dict) and c.get("tool")):
                bad.append("%s: every entry of calls is {\"tool\": name, \"args\": {the arguments that matter}}" % t["id"])
        cited = e.get("rules") if isinstance(e.get("rules"), list) else []
        if not cited:
            bad.append("%s: cite the rule ids the expectation comes from under \"rules\"" % t["id"])
        for rid in cited:
            if rid not in known:
                bad.append("%s: cites %r, which is not a rule id" % (t["id"], rid))
            elif rid not in live:
                bad.append("%s: cites %s, which is not a live rule" % (t["id"], rid))
        for p in e.get("promises") or []:
            if not (isinstance(p, dict) and p.get("amount") is not None and p.get("date")):
                bad.append("%s: every promise needs product_id, amount and date" % t["id"])
    for k in exp:
        if k not in {t["id"] for t in topics}:
            bad.append("%s: not a topic in topics.json" % k)
    return bad


def main(exp_p="expectations.json", rules_p="rules.json", topics_p="topics.json"):
    try:
        exp, rules, topics = json.load(open(exp_p)), json.load(open(rules_p))["rules"], json.load(open(topics_p))
    except Exception as e:
        print("FAIL cannot read inputs: %s" % e)
        return 1
    import inputs
    bad = problems(exp, rules, topics, inputs.mode() == "final")
    for b in bad:
        print("FAIL", b)
    print("check_expectations:", "FAILED" if bad else "ok", "| %d topics" % len(topics))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
