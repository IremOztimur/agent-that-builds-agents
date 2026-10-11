"""Offline check of how customers are given a way of talking. Run: python3 builder/tests/test_styles.py"""
import pathlib, sys

T = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(T))
import styles

ids = ["PUB-%02d" % n for n in range(1, 14)]
a, b = styles.assign(ids), styles.assign(ids, 1)
assert set(a.values()) == {"talkative", "pieces", "corrects", "asks_back", "in_words", None}, "every way of talking, and plain, appears"
assert styles.assign(list(reversed(ids))) == a, "the assignment depends on the ids, not their order"
assert styles.assign(ids) == a, "stable between rounds"
assert all(a[i] != b[i] for i in ids), "the hold-out gives every customer a different style"
assert styles.assign([]) == {}
# a rerun of one customer keeps its style: the assignment is made over all customers, then filtered
assert {i: a[i] for i in ["PUB-06"]} == {"PUB-06": styles.assign(ids)["PUB-06"]}
print("ok: styles")
