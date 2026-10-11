"""Offline checks of the rules schema and the expectations gate (no platform). Run: python3 builder/tests/test_oracle_gate.py"""
import contextlib, io, json, os, pathlib, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "builder" / "tools"))
import check_expectations, check_rules
from builder.lib import workdir

BRIEF = "Say hello. This call is recorded. Offer the floor once.\n"
API = {"enum": ["a"]}
GOOD = {"id": "r1", "quote": "This call is recorded.", "class": "speech", "status": "decided", "stage": "open", "kind": "wording",
        "wording": "This call is recorded.", "applies": "at the start of every call"}


def rules_check(rules, brief=BRIEF):
    w = pathlib.Path(tempfile.mkdtemp())
    (w / "brief.md").write_text(brief)
    (w / "tools.json").write_text(json.dumps(API))
    json.dump({"brief_lines": len(brief.splitlines()), "rules": rules}, open(w / "rules.json", "w"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_rules.main(str(w / "rules.json"), str(w / "brief.md"), str(w / "tools.json"))
    return code, out.getvalue()


assert rules_check([GOOD])[0] == 0, rules_check([GOOD])[1]
assert rules_check([{**GOOD, "kind": "invented"}])[0] == 1                                 # unknown kind
assert rules_check([{k: v for k, v in GOOD.items() if k != "applies"}])[0] == 1            # no situation
assert rules_check([{**GOOD, "wording": "This call is monitored."}])[0] == 1               # wording not in the brief
assert rules_check([{**GOOD, "depends_on": ["r9"]}])[0] == 1                               # unknown dependency
assert rules_check([{**GOOD, "status": "superseded", "kind": None, "applies": ""}])[0] == 0  # dead rules are not checked for kind

RULES = [GOOD, {**GOOD, "id": "r2", "status": "superseded"}]
TOPICS = [{"id": "T1"}, {"id": "T2"}]
E = {"outcome": "promise", "reason": None, "promises": [{"product_id": "p1", "amount": 10.0, "date": "2026-10-14"}], "notes": [],
     "callbacks": [], "transfers": [], "must_state": [], "must_not": [], "rules": ["r1"]}
assert check_expectations.problems({"T1": E, "T2": E}, RULES, TOPICS) == []
assert any("T2" in p and "no entry" in p for p in check_expectations.problems({"T1": E}, RULES, TOPICS))
assert any("cite" in p for p in check_expectations.problems({"T1": E, "T2": {**E, "rules": []}}, RULES, TOPICS))
assert any("not a live rule" in p for p in check_expectations.problems({"T1": E, "T2": {**E, "rules": ["r2"]}}, RULES, TOPICS))
assert any("not a rule id" in p for p in check_expectations.problems({"T1": E, "T2": {**E, "rules": ["r9"]}}, RULES, TOPICS))
assert any("outcome" in p for p in check_expectations.problems({"T1": E, "T2": {**E, "outcome": ""}}, RULES, TOPICS))
assert any("promise needs" in p for p in check_expectations.problems({"T1": E, "T2": {**E, "promises": [{"amount": 5}]}}, RULES, TOPICS))

# the topics the agent sees never carry the expected values, the checks or the identity answers
for cases in ("A", "B", "AB"):
    for t in workdir.topics(cases):
        assert not {"expected", "checks", "identity"} & set(t), t
assert len(workdir.topics("AB")) == 13 and len(workdir.topics("A")) == 10 and len(workdir.topics("B")) == 3
print("ok: oracle gate")
