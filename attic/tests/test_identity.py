"""Offline sanity checks for the identity path. Run: python3 builder/tests/test_identity.py

1. every embedded snippet runs locally with an empty vars table and never raises
2. the controller can never write trusted state, whatever the model sends
3. verification state follows only the bank's answer; a failed or empty bank answer never verifies
4. the account gate fails closed and authorisation is single-use
5. lint rejects a workflow whose protected read is reachable without the gate
"""
import copy, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import compile as C, gates, lint, policy_a
from nodes import Api

API = Api.load(HERE.parents[1] / "build-the-builder_pack" / "tools" / "openapi.json")
P = policy_a.POLICY
CFG = C.identity_cfg(P["identity"])


def run(src, vars_, params=None):
    exec(compile(src, "<snippet>", "exec"), {"vars": vars_, "params": params if params is not None else {}})
    return vars_


def bank(v, ok="true", verified="true", all_="false", left="3", hint=""):
    v.update(vf_ok=ok, vf_verified=verified, vf_all=all_, vf_left=left, vf_hint=hint)


def controller(v, field, answer):
    return run(gates.controller(CFG), v, {"field": field, "answer": answer})


def test_empty_vars():
    for src in (gates.controller(CFG), gates.after_verify(CFG), gates.gate_account(CFG), gates.after_account(C.account_cfg(P))):
        run(src, dict())
    v = run(gates.gate_account(CFG), dict())
    assert v["auth_account"] == "denied", v


def test_controller_is_not_trusted():
    for src in (gates.controller(CFG),):
        assert not any(p in src for p in ("vars['auth_", "vars['idok_", "vars['id_state", "vars['acct_used")), "controller writes trusted state"
    for field, ans in (("date_of_birth", "1988-03-14"), ("date_of_birth", "14 March 1988"), ("date_of_birth", "1988-13-45"), ("phone_last4", "4471"), ("bogus", "x"), ("", "")):
        v = controller(dict(), field, ans)
        assert not any(k.startswith(("auth_", "idok_")) or k in ("id_state", "acct_used") for k in v), (field, ans, v)
    v = controller(dict(), "date_of_birth", "1988-03-14")
    assert v["go"] == "verify" and v["cand_field"] == "date_of_birth" and v["cand_answer"] == "1988-03-14", v
    v = controller(dict(), "date_of_birth", "14 March 1988")      # not YYYY-MM-DD: nothing is sent to the bank
    assert v["go"] == "" and "cand_answer" not in v, v
    v = controller(dict(), "phone_last4", "4471")                 # out of order: dob is pending
    assert v["go"] == "" and P["identity"]["questions"][0]["ask"] in v["say"], v
    v = controller(dict(idok_date_of_birth="yes"), "phone_last4", "44 71")
    assert v["go"] == "verify" and v["cand_answer"] == "4471", v
    v = controller(dict(idok_date_of_birth="yes"), "phone_last4", "447")
    assert v["go"] == "", v


def test_verification_follows_the_bank():
    # first answer right
    v = dict(cand_field="date_of_birth"); bank(v, all_="false")
    v = run(gates.after_verify(CFG), v)
    assert v["idok_date_of_birth"] == "yes" and v["id_state"] == "open", v
    # second answer right and the bank says all verified
    v["cand_field"] = "phone_last4"; bank(v, all_="True")
    v = run(gates.after_verify(CFG), v)
    assert v["id_state"] == "passed", v
    # the bank says all verified but a question was never answered: not passed
    v = dict(cand_field="phone_last4"); bank(v, all_="true")
    v = run(gates.after_verify(CFG), v)
    assert v.get("id_state") != "passed", v
    # empty bank answer (call failed): nothing verified, retry, fails after the cap
    v = dict(cand_field="date_of_birth")
    for i in range(CFG["max_unread"]):
        assert "idok_date_of_birth" not in v and v.get("id_state") != "failed"
        v = run(gates.after_verify(CFG), v)
    assert "idok_date_of_birth" not in v and v["id_state"] == "failed", v
    # wrong answer: asked again; last wrong answer ends the check
    v = dict(cand_field="date_of_birth"); bank(v, verified="false", left="1")
    v = run(gates.after_verify(CFG), v)
    assert "idok_date_of_birth" not in v and v["id_state"] == "open", v
    v = dict(cand_field="date_of_birth"); bank(v, verified="false", left="0")
    v = run(gates.after_verify(CFG), v)
    assert v["id_state"] == "failed", v
    # day and month swapped: no state change
    v = dict(cand_field="date_of_birth"); bank(v, ok="true", verified="false", left="3", hint="day_month_swapped")
    v = run(gates.after_verify(CFG), v)
    assert "idok_date_of_birth" not in v and v["id_state"] == "open" and v["say"] == CFG["swapped"], v


def test_gate_fails_closed_and_is_single_use():
    good = dict(id_state="passed", idok_date_of_birth="yes", idok_phone_last4="yes")
    assert run(gates.gate_account(CFG), dict(good))["auth_account"] == "granted"
    for broken in (dict(good, id_state="open"), dict(good, id_state="failed"), {k: v for k, v in good.items() if k != "idok_phone_last4"}, dict(good, acct_used="yes"), dict()):
        assert run(gates.gate_account(CFG), dict(broken))["auth_account"] == "denied", broken
    v = run(gates.after_account(C.account_cfg(P)),
            dict(auth_account="granted", acct_ok="true", now="2026-10-14T11:00", products_json=json.dumps([dict(product_id="p1", type="credit_card", card_last4="4821", past_due=420.0, minimum_payment=126.0, days_late=6)])))
    assert v["auth_account"] == "used" and v["acct_used"] == "yes" and v["acct_state"] == "ok" and "4821" in v["debt_line"] and "420.00" in v["debt_line"], v
    v2 = run(gates.gate_account(CFG), dict(good, **{k: v[k] for k in ("acct_used",)}))
    assert v2["auth_account"] == "denied", "authorisation must be single-use"
    v = run(gates.after_account(C.account_cfg(P)), dict(auth_account="granted", acct_ok="false"))
    assert v["auth_account"] == "used" and v["acct_state"] == "error", "consumed even when the read failed"


def test_lint():
    wf = C.compile_identity(P, API)
    protected = {P["account"]["op"]: P["account"]["auth_var"], P["promise"]["op"]: P["promise"]["auth_var"]}
    assert lint.lint(wf, API, protected) == []
    bad = copy.deepcopy(wf)
    bad["nodes"]["after_verify"]["transitions"].insert(0, {"target_node": "fetch_account", "description": "x", "condition": {"operator": "always"}})
    assert any(p.startswith("G1") for p in lint.lint(bad, API, protected))
    bad = copy.deepcopy(wf)
    bad["nodes"]["identity"]["tools"].append(bad["nodes"]["fetch_account"]["pre_actions"][0])
    assert any(p.startswith("G2") for p in lint.lint(bad, API, protected))
    bad = copy.deepcopy(wf)
    tool = bad["nodes"]["identity"]["tools"][0]["function"]["parameters"]["properties"]["code"]
    tool["default"] += "\nvars['idok_phone_last4'] = 'yes'\n"
    assert any(p.startswith("G3") for p in lint.lint(bad, API, protected))
    bad = copy.deepcopy(wf)
    bad["nodes"]["verify_call"]["pre_actions"][0]["function"]["parameters"]["properties"]["body"]["properties"]["answer"]["default"] = "{{model_said}}"
    assert any(p.startswith("G4") for p in lint.lint(bad, API, protected))


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
