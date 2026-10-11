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
# a workflow changed after the last full round is measured once, even when that round was clean
clean = [{"name": "r2", "only": None, "failed": [], "total": 5, "pub": 4}]
assert stoprule.verdict(clean, ALL).startswith("STOP")
assert not stoprule.needs_measuring(clean, ALL, 4) and stoprule.needs_measuring(clean, ALL, 5)
assert not stoprule.needs_measuring([], ALL, 1)
# the whole sequence that deadlocked: clean round, hold-out round, repair published, measured once, then STOP again
seq = [{"name": "r1", "only": None, "failed": ["a"], "total": 5, "pub": 1}, {"name": "r2", "only": None, "failed": [], "total": 5, "pub": 2},
       {"name": "h1", "only": None, "failed": ["a", "b"], "total": 5, "pub": 2, "style": "holdout"}]
assert stoprule.verdict(seq, ALL).startswith("STOP") and not stoprule.needs_measuring(seq, ALL, 2)       # unchanged workflow: no rerun
assert stoprule.needs_measuring(seq, ALL, 3)                                                              # repaired: measure it
seq.append({"name": "r3", "only": None, "failed": [], "total": 5, "pub": 3})
assert stoprule.verdict(seq, ALL).startswith("STOP") and not stoprule.needs_measuring(seq, ALL, 3)
assert stoprule.best(seq, ALL)["name"] == "r3"                                                            # the latest on a tie ships
print("ok: style rounds")
