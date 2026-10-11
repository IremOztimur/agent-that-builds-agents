"""Offline checks of the repair stop rule. Run: python3 builder/tests/test_stop_rule.py"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from stoprule import verdict

IDS = ["c%02d" % i for i in range(13)]


def run(failed, only=None):
    return {"only": only, "failed": failed, "total": 13}


stop = lambda r: (verdict(r, IDS) or "").startswith("STOP")
assert verdict([], IDS) is None
assert stop([run([])]), "all pass"
assert not stop([run(["c01"])]), "one round with one failure: a repair has not been tried yet"
assert stop([run(["c01"]), run(["c01"])]), "strong and unchanged: stop"
assert not stop([run(["c01", "c02"]), run(["c01"])]), "improving: continue"
assert stop([run(["c01"]), run([], ["c01"])]), "a failure that passes alone is noise: nothing left"
w = ["c01", "c02", "c03", "c04", "c05", "c06"]
assert not stop([run(w), run(w)]), "weak and unchanged once: one more try"
assert stop([run(w), run(w), run(w)]), "weak and unchanged twice: stop"
assert not stop([run(w), run(w[:5]), run(w[:3])]) and stop([run(w), run(w[:5]), run(w[:3]), run(w[:2])]), "improving ends at four rounds"
assert not stop([run(["c01", "c02", "c03"]), run(["c01"]), run(["c05"])]), "a different single failure is not 'the same'"
print("ok: stop rule")
