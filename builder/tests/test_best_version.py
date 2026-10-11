"""Offline: finalize publishes the best MEASURED version, not the latest one. Run: python3 builder/tests/test_best_version.py"""
import json, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from builder.lib import finalize

class T:
    lines = []
    def line(self, k, t): self.lines.append((k, t))

def fake(rounds, latest):
    w = pathlib.Path(tempfile.mkdtemp()); s = pathlib.Path(tempfile.mkdtemp())
    (w / "versions").mkdir(); (w / ".sealed").write_text(str(s))
    json.dump([{"id": "c%02d" % i} for i in range(13)], open(w / "topics.json", "w"))
    json.dump(rounds, open(s / "rounds.json", "w"))
    pubs = []
    for n in (1, 2, 3, 4):
        json.dump({"version": n}, open(w / "versions" / ("pub-%d.json" % n), "w")); pubs.append({"seq": n, "file": "versions/pub-%d.json" % n})
    json.dump(pubs, open(w / "published.json", "w")); json.dump({"version": latest}, open(w / "workflow.json", "w"))
    return w

r = lambda name, failed, pub, only=None: {"name": name, "only": only, "failed": failed, "total": 13, "pub": pub}
# the real run: 8, 11, 11 and then an unmeasured publish #4 sitting in workflow.json
w = fake([r("r1", list("abcde"), 1), r("r2", ["c12", "c13"], 2), r("r3", ["c10", "c12"], 3), r("r4", ["c10", "c12"], 4, only=["c01", "c10", "c11"])], latest=4)
t = T(); chosen = finalize.best_measured(w, t)
assert chosen == {"version": 3}, chosen          # best full round (11 of 13, latest of the two), not the partial v4
assert "replaces the later" in t.lines[-1][1], t.lines
# nothing measured: leave workflow.json alone
w = fake([], latest=4); assert finalize.best_measured(w, T()) is None
print("ok: best measured version")
