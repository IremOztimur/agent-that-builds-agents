"""Offline check: a conversation node needs a turn cap with a target, and the cap is small. Run: python3 builder/tests/test_lint_caps.py"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import lint


def wf(**node):
    end = {"node_type": "end_call", "transitions": [], "terminal": {"function": {"name": "bye", "handler": "__function__:end_call"}}}
    a = {"node_type": "conversation", "task_message": "t", "transitions": [{"target_node": "bye", "description": "d", "condition": {"operator": "always"}}], **node}
    return {"initial_node": "a", "nodes": {"a": a, "bye": end}}


def problems(w):
    return lint.lint(w)[0]


assert not any("max_turn" in p or "max_node_turns" in p for p in problems(wf(max_node_turns=12, max_turn_transition="bye")))
assert any("no max_turn_transition" in p for p in problems(wf(max_node_turns=12)))
assert any("max_node_turns is 40" in p for p in problems(wf(max_node_turns=40, max_turn_transition="bye")))
print("ok: lint turn caps")
