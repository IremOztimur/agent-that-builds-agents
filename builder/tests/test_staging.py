"""Offline checks of the basic-customers selection, the smoke gate bookkeeping and the style-aware stop rule. Run: python3 builder/tests/test_staging.py"""
import json, pathlib, sys

T = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(T))
import staging, stoprule

cases = json.load(open(T.parents[1] / "build-the-builder_pack" / "public-test-set.json"))
ids = staging.smoke_ids(cases)
fam = {c["id"]: c["family"] for c in cases}
assert len(ids) <= 6 and len({fam[i] for i in ids if len(next(c for c in cases if c["id"] == i)["products"]) == 1}) == len([i for i in ids if len(next(c for c in cases if c["id"] == i)["products"]) == 1]), ids   # one per family
assert any(len(next(c for c in cases if c["id"] == i)["products"]) > 1 for i in ids), "one customer with several products"
assert next(c["id"] for c in cases if c["level"] == "easy") in ids, "the easiest kind comes first"
assert staging.smoke_ids([]) == []

ALL = ["a", "b", "c", "d", "e"]
log = [{"name": "r1", "only": None, "failed": ["a", "b"], "total": 5, "pub": 1},
       {"name": "s2", "only": ["a"], "failed": [], "total": 1, "pub": 2, "smoke": True},          # a smoke run must not clear a failure of the full round
       {"name": "r2", "only": None, "failed": ["a"], "total": 5, "pub": 3, "style": "talkative"},  # another way of talking is not a round
       ]
full = stoprule.full_rounds(log, ALL)
assert len(full) == 1 and full[0]["failed"] == {"a", "b"}, full
assert stoprule.best(log, ALL)["name"] == "r1"
print("ok: staging")
