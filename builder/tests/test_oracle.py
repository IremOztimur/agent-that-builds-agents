"""Offline checks of the derived-expectation oracle (no platform). Run: python3 builder/tests/test_oracle.py"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import oracle

E = {"outcome": "promise", "reason": None, "promises": [{"product_id": "p1", "amount": 1250, "date": "2026-10-23"}], "notes": [],
     "callbacks": [], "transfers": [], "must_state": ["says: This call is recorded."], "must_not": ["offer a second amount"], "rules": ["r1"]}
KNOWN = {"outcome": "promise", "reason": None, "promises": [{"product_id": "p1", "amount": 1250.0, "date": "2026-10-23"}], "notes": [], "callbacks": [], "transfers": []}

exp = oracle.to_expected(E)
assert exp["outcome"] == "promise" and exp["reason"] is None and exp["promises"][0]["amount"] == 1250 and "must_state" not in exp
assert oracle.checks(E)[0].startswith("the agent states:") and oracle.checks(E)[1].startswith("the agent does not:") and "recorded" in oracle.checks(E)[-1]

# derived expectations against known ones: parts are named, nothing else
assert oracle.mismatch(E, KNOWN) == []
assert oracle.mismatch({**E, "outcome": "no_promise", "reason": "hardship"}, KNOWN) == ["outcome"]
assert oracle.mismatch({**E, "promises": [{"product_id": "p1", "amount": 1250, "date": "2026-10-24"}]}, KNOWN) == ["promises"]
assert oracle.mismatch({**E, "notes": [{"product_id": "p1", "reason": "refused"}], "transfers": [{"queue": "x"}]}, KNOWN) == ["notes", "transfers"]

# mandated wording is a plain text check
RULES = [{"id": "r1", "wording": "This call is recorded."}, {"id": "r2", "wording": "You may ask for a callback."}, {"id": "r3"}]
assert oracle.wording_misses(E, RULES, "Hello. This call  is recorded, and we help.") == []
assert oracle.wording_misses(E, RULES, "Hello, how can I help?") == ["r1"]
assert oracle.wording_misses({**E, "must_state": []}, RULES, "Hello") == []          # not required in this topic
print("ok: oracle")
