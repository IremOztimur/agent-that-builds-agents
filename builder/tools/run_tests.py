"""Run tests.json against workflow.json with the local code runner. Brief-independent.

    python3 tools/run_tests.py tests.json workflow.json

A test: {"rule", "name", "target", "hook": "pre|post|none", "vars", "params", "config", "result", "expect": {"vars.x": v, "config.url": v, "result.data.k": v}}.
An expect key ending in "~" checks that the value contains the given text.
"""
import json, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_code import find

tests = json.load(open(sys.argv[1]))
tests = tests["tests"] if isinstance(tests, dict) else tests
wf = json.load(open(sys.argv[2]))
ok = 0
for t in tests:
    hook = t.get("hook") if t.get("hook") in ("pre", "post") else None
    src = find(wf, t["target"], hook)
    label = "%s %s" % (t.get("rule", "?"), t.get("name", ""))
    if not src:
        print("FAIL", label, "- no code for target", t["target"]); continue
    g = {"vars": json.loads(json.dumps(t.get("vars", {}))), "params": t.get("params", {}), "config": json.loads(json.dumps(t.get("config", {}))), "result": json.loads(json.dumps(t.get("result", {})))}
    try:
        exec(compile(src, "<%s>" % t["target"], "exec"), g)
    except Exception as e:
        print("FAIL", label, "- raised", repr(e)[:120]); continue
    errs = []
    for path, want in t.get("expect", {}).items():
        contains = path.endswith("~")
        node = g
        for part in path.rstrip("~").split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if (contains and str(want) not in str(node)) or (not contains and str(node) != str(want) and node != want):
            errs.append("%s: expected %r, got %r" % (path, want, node))
    print("PASS" if not errs else "FAIL", label, "; ".join(errs))
    ok += not errs
print("tests: %d / %d passed" % (ok, len(tests)))
sys.exit(0 if ok == len(tests) else 1)
