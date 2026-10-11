"""Offline sanity checks for the promise flow. Run: python3 builder/tests/test_promise.py

Limits (calendar, deadline, floor, full amount), read-back freshness, the write gate and the retry cap, all on the
policy code that runs inside the workflow, with a fake vars table.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import compile as C, gates, lint, policy_a
from nodes import Api

P = policy_a.POLICY
GATE = C.gate_cfg(P)
PRM = C.promise_cfg(P)
TURN = P["promise"]["turn_key"]


def run(src, vars_, params=None):
    exec(compile(src, "<snippet>", "exec"), {"vars": vars_, "params": params if params is not None else {}})
    return vars_


def account(days=6, kind="credit_card", past_due=420.0, floor=126.0, now="2026-10-14T11:00"):
    prod = dict(product_id="p1", type=kind, past_due=past_due, days_late=days)
    prod["minimum_payment" if kind == "credit_card" else "instalment_amount"] = floor
    if kind == "credit_card":
        prod["card_last4"] = "4821"
    v = dict(id_state="passed", idok_date_of_birth="yes", idok_phone_last4="yes", auth_account="granted", acct_ok="true", now=now,
             products_json=json.dumps([prod]))
    return run(gates.after_account(C.account_cfg(P)), v)


def propose(v, amount, date, turn=1):
    v[TURN] = turn
    return run(gates.proposal(PRM), v, {"amount": amount, "date": date})


def confirm(v, decision, turn):
    v[TURN] = turn
    return run(gates.confirmation(PRM), v, {"decision": decision})


def gate(v):
    return run(gates.gate_promise(GATE), v)["auth_promise"]


def test_facts():
    v = account(days=6)
    f = json.loads(v["facts_json"])[0]
    assert v["acct_state"] == "ok" and f["deadline"] == "2026-11-02" and f["floor"] == 126.0 and "2026-10-26" not in f["valid"], f   # early band, holiday skipped
    assert v["debt_line"].endswith(P["account"]["first_ask"]) and "420.00" in v["debt_line"]
    f = json.loads(account(days=14, kind="car_loan", past_due=1250.0, floor=400.0)["facts_json"])[0]
    assert f["deadline"] == "2026-10-23" and f["floor"] == 400.0, f                                                                # late band
    assert account(days=0)["acct_state"] == "error" and account(days=99)["acct_state"] == "error", "no band: fail closed"


def test_limits():
    base = account(days=14, kind="car_loan", past_due=1250.0, floor=400.0)          # late band, deadline 23 October
    v = propose(dict(base), 1250.0, "2026-11-06")
    assert v["prop_state"] == "" and "Friday 23 October" in v["say"] and v["go"] == "", v
    v = propose(dict(base), 1250.0, "2026-10-17")                                    # a Saturday
    assert v["prop_state"] == "" and "Monday 19 October" in v["say"], v
    v = propose(dict(base), 1250.0, "2026-10-13")
    assert v["prop_state"] == "" and "passed" in v["say"], v
    v = propose(dict(base), 399.99, "2026-10-16")
    assert v["prop_state"] == "" and "400.00" in v["say"], v
    v = propose(dict(base), 1250.01, "2026-10-16")
    assert v["prop_state"] == "" and "1250.00" in v["say"], v
    v = propose(dict(base), "four hundred", "2026-10-16")
    assert v["prop_state"] == "" and v["go"] == "", v
    v = propose(dict(base), 400, "next friday")
    assert v["prop_state"] == "", v
    early = account(days=5, kind="personal_loan", past_due=540.0, floor=180.0)      # PUB-07 shape: holiday proposed
    v = propose(dict(early), 540.0, "2026-10-26")
    assert "Tuesday 27 October" in v["say"], v
    v = propose(dict(base), 400, "2026-10-14")                                       # today, floor, boundary values are fine
    assert v["prop_state"] == "readback" and v["prop_amount"] == 400.0 and v["prop_date"] == "2026-10-14", v


def test_read_back_and_confirmation_freshness():
    base = account(days=6)
    v = propose(dict(base), 420.0, "2026-10-14", turn=1)
    assert "420.00" in v["say"] and "credit card ending 4821" in v["say"] and "Wednesday 14 October" in v["say"] and v["conf_state"] == "", v
    # re-reporting the identical proposal changes nothing: same id, same clock, the confirmation on a later turn still counts
    again = propose(dict(v), 420.0, "2026-10-14", turn=2)
    assert again["prop_id"] == v["prop_id"] and again["prop_turn"] == v["prop_turn"] and again["prop_seq"] == v["prop_seq"] and "420.00" in again["say"], again
    assert confirm(dict(again), "yes", turn=2)["go"] == "promise"
    assert confirm(propose(dict(v), 420.0, "2026-10-14", turn=1), "yes", turn=1)["go"] == "", "same-turn repeat must not confirm"
    # confirming in the same user turn as the proposal does not count
    w = confirm(dict(v), "yes", turn=1)
    assert w["go"] == "" and w.get("conf_state") == "", w
    # confirmation with no proposal on the table
    w = confirm(dict(base), "yes", turn=2)
    assert w["go"] == "" and P["promise"]["lines"]["need_proposal"] == w["say"], w
    # a later turn, clear yes: authorisation can be granted
    w = confirm(dict(v), "yes", turn=2)
    assert w["go"] == "promise" and w["conf_for"] == w["prop_id"], w
    assert gate(dict(w)) == "granted"
    # a "no" clears the proposal; a late "yes" for it is meaningless
    n = confirm(dict(v), "no", turn=2)
    assert n["go"] == "" and n["prop_state"] == "" and gate(dict(n)) == "denied", n
    assert confirm(dict(n), "yes", turn=3)["go"] == "", "yes after a no must not confirm"
    # the customer changes the date after the confirmation: new read-back, old confirmation is gone
    w2 = propose(dict(w), 420.0, "2026-10-15", turn=3)
    assert w2["conf_state"] == "" and w2["prop_id"] != w["prop_id"] and gate(dict(w2)) == "denied", w2
    # a stale confirmation for an earlier proposal does not authorise the current one
    stale = dict(w2, conf_state="yes", conf_for=w["prop_id"])
    assert gate(stale) == "denied"
    # unknown or garbled decision is not a yes
    assert confirm(dict(v), "maybe", turn=2)["go"] == ""


def test_gate_fails_closed():
    base = account(days=6)
    v = propose(dict(base), 420.0, "2026-10-14", turn=1)
    ok = confirm(dict(v), "yes", turn=2)
    assert gate(dict(ok)) == "granted"
    for name, broken in (("tampered amount", dict(ok, prop_amount=9999.0)), ("tampered date", dict(ok, prop_date="2026-12-24")),
                         ("weekend", dict(ok, prop_date="2026-10-17")), ("identity open", dict(ok, id_state="open")),
                         ("missing dob", {k: x for k, x in ok.items() if k != "idok_date_of_birth"}), ("no confirmation", dict(ok, conf_state="")),
                         ("attempts used", dict(ok, promise_attempts=2)), ("already recorded", dict(ok, promise_state="recorded")),
                         ("no facts", {k: x for k, x in ok.items() if k != "facts_json"}), ("unknown product", dict(ok, prop_product="p9"))):
        assert gate(broken) == "denied", name
    assert gate(dict()) == "denied"
    g = run(gates.gate_promise(GATE), dict(ok, pr_ok="true", pr_id="stale"))
    assert g["pr_ok"] == "" and g["pr_id"] == "", "a stale bank answer must not survive into the next attempt"


def test_after_promise_follows_the_bank():
    cfg = {"max_attempts": P["promise"]["max_attempts"]}
    after = lambda v: run(gates.after_promise(cfg), v)
    v = after(dict(auth_promise="granted", pr_ok="true", pr_id="pr_1"))
    assert v["promise_state"] == "recorded" and v["auth_promise"] == "used", v
    assert after(dict(auth_promise="granted", pr_ok="true", pr_id=""))["promise_state"] == "retry", "ok without a promise id is not a recording"
    assert after(dict(auth_promise="granted", pr_ok="false", pr_id=""))["promise_state"] == "retry"
    assert after(dict(auth_promise="granted"))["promise_state"] == "retry", "no answer at all"
    v = after(dict(auth_promise="granted", pr_ok="", promise_attempts=1))
    assert v["promise_state"] == "failed" and v["promise_attempts"] == 2, v
    assert gate(dict(v)) == "denied"


def test_lint_and_compile():
    api = Api.load(HERE.parents[1] / "build-the-builder_pack" / "tools" / "openapi.json")
    wf = C.compile_identity(P, api)
    protected = {P["account"]["op"]: P["account"]["auth_var"], P["promise"]["op"]: P["promise"]["auth_var"]}
    assert lint.lint(wf, api, protected) == []
    assert json.dumps(C.compile_identity(P, api), sort_keys=True) == json.dumps(wf, sort_keys=True), "compile must be deterministic"
    import copy
    bad = copy.deepcopy(wf)
    bad["nodes"]["negotiate"]["transitions"].insert(0, {"target_node": "create_promise_call", "description": "x", "condition": {"operator": "always"}})
    assert any(p.startswith("G1") for p in lint.lint(bad, api, protected))
    bad = copy.deepcopy(wf)
    bad["nodes"]["negotiate"]["tools"][0]["function"]["parameters"]["properties"]["code"]["default"] += "\nvars['auth_promise'] = 'granted'\n"
    assert any(p.startswith("G3") for p in lint.lint(bad, api, protected))


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
