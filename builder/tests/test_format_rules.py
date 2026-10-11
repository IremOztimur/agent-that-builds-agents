"""Offline check: the format rules the agent reads and the lint that enforces them say the same thing. Run: python3 builder/tests/test_format_rules.py"""
import pathlib, re, sys

B = pathlib.Path(__file__).resolve().parents[1]
rules = (B / "skills" / "compose-workflow" / "format-rules.md").read_text()
listed = set(re.findall(r"^\| ([FW]\d+) \|", rules, re.M))
used = set(re.findall(r"\[([FW]\d+)\]", (B / "tools" / "lint.py").read_text()))
assert used <= listed, "lint cites a rule the agent is never told: %s" % sorted(used - listed)
assert listed <= used, "a format rule nothing checks: %s" % sorted(listed - used)
skill = (B / "skills" / "compose-workflow" / "SKILL.md").read_text()
assert "format-rules.md" in skill and "check_workflow.py" in skill
sys.path.insert(0, str(B / "tools"))
import lint
bad, warn, _ = lint.lint({"initial_node": "a", "nodes": {"a": {"node_type": "conversation", "tools": [], "loop_prompt": "x", "transitions": []}}})
assert any(p.startswith("[F12]") for p in bad) and all(re.match(r"\[[FW]\d+\]", p) for p in bad + warn), bad
print("ok: format rules")
