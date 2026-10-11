"""Offline checks of the phase gates (no platform). Run: python3 builder/tests/test_design_gate.py"""
import json, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from builder.lib import design

WF = {"initial_node": "a", "nodes": {"a": {"node_type": "conversation", "tools": [{"function": {"name": "create_promise"}}], "transitions": []}}}
RULES = [{"id": "r1", "class": "gate", "status": "decided", "quote": "Never read the balance before identity is verified"},
         {"id": "r2", "class": "flow", "status": "decided", "quote": "Offer the floor once"},
         {"id": "r3", "class": "speech", "status": "decided", "quote": "Say goodbye politely"},
         {"id": "r4", "class": "calc", "status": "superseded", "quote": "Old limit of 5"}]


def check(rows):
    w = pathlib.Path(tempfile.mkdtemp())
    json.dump({"rules": RULES}, open(w / "rules.json", "w"))
    json.dump(WF, open(w / "workflow.json", "w"))
    json.dump({"rows": rows}, open(w / "design.json", "w"))
    return design.check(w)


ok = [{"rules": ["r1", "r2"], "mechanism": "code", "where": "pre hook of create_promise"}, {"rules": ["r3"], "mechanism": "prompt", "where": "system prompt"}]
assert check(ok) == [], check(ok)
assert any("r3" in p and "no row" in p for p in check(ok[:1])), "a live rule without a row must fail"
assert check(ok[:1] + [{"rules": ["r3"], "mechanism": "prompt", "where": ""}]) == []
bad = check([{"rules": ["r1"], "mechanism": "prompt", "where": "x"}, {"rules": ["r2"], "mechanism": "prompt", "where": "x"}, ok[1]])
assert sum("prompt-only but is a hard rule" in p for p in bad) == 2, bad          # a gate rule, and a counted rule ("once")
assert any("names no node or tool" in p for p in check([{"rules": ["r1", "r2"], "mechanism": "code", "where": "somewhere invented"}, ok[1]]))
print("ok: design gate")
