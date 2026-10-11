"""Offline checks of the repair stop rule. Run: python3 builder/tests/test_stop_rule.py"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from stoprule import best, verdict

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
assert not stop([run(w), run(w)]), "weak and not improving once: one more try"
assert stop([run(w), run(w), run(w)]), "weak and unchanged twice: stop"
assert not stop([run(w), run(w[:5]), run(w[:3])]) and stop([run(w), run(w[:5]), run(w[:3]), run(w[:2])]), "improving ends at four rounds"
assert stop([run(["c01", "c02", "c03"]), run(["c01"]), run(["c05"])]), "failures moved but did not go down: stop"
assert stop([run(["c11", "c12"]), run(["c10", "c12"])]), "the real run: 2 failures, then 2 again, one of them the same"
assert "c12" in verdict([run(["c11", "c12"]), run(["c10", "c12"])], IDS)
r = lambda failed, pub: {"name": "x", "only": None, "failed": failed, "total": 13, "pub": pub}
assert best([r(w, 1), r(["c01", "c02"], 2), r(["c03", "c04"], 3)], IDS)["pub"] == 3, "ties go to the latest"
assert best([r(["c01", "c02"], 2), r(w, 3)], IDS)["pub"] == 2, "an unmeasured or worse later version is not chosen"
assert best([], IDS) is None
print("ok: stop rule")
