"""Offline check: a run with another way of talking is not a round. Run: python3 builder/tests/test_style_rounds.py"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import stoprule

ALL = ["a", "b", "c", "d", "e"]
log = [{"name": "r1", "only": None, "failed": ["a", "b"], "total": 5, "pub": 1},
       {"name": "r2", "only": None, "failed": ["a"], "total": 5, "pub": 3, "style": "talkative"}]
full = stoprule.full_rounds(log, ALL)
assert len(full) == 1 and full[0]["failed"] == {"a", "b"}, full
assert stoprule.best(log, ALL)["name"] == "r1"
assert stoprule.is_dead([1, 1, 0, 1]) and not stoprule.is_dead([1, 5, 1, 1]) and not stoprule.is_dead([1, 1])   # one slow customer is not an outage
print("ok: style rounds")
