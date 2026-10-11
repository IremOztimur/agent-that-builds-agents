"""The three phases, in order, each with one skill and one deterministic gate. All three run in the same agent session; a phase only starts when the previous gate passed."""
import json, subprocess, sys

PHASES = [
    {"n": 0, "skill": "read-brief", "prompt": "Phase 0 of 3: use the read-brief skill.",
     "reads": ["inputs.json"]},
    {"n": 1, "skill": "compose-workflow", "prompt": "Phase 1 of 3: use the compose-workflow skill.",
     "reads": ["docs/workflow-format.md", "docs/tools-and-code.md", "examples/base-agent.json"]},
    {"n": 2, "skill": "test-and-repair", "prompt": "Phase 2 of 3: use the test-and-repair skill.",
     "reads": []},
]


def gate(n, work, seen):
    """Problems that keep the phase from counting as done. An empty list means the next phase may start."""
    reads = list(PHASES[n]["reads"])
    if n == 0:
        m = json.load(open(work / "inputs.json"))
        reads += [m["brief"], m["tools"]]
    bad = [f"you have not read {p} in this phase" for p in reads if p.lower() not in seen]
    if n == 0:
        out = subprocess.run([sys.executable, "tools/check_rules.py"], cwd=work, capture_output=True, text=True).stdout
        if "check_rules: ok" not in out:
            bad.append("tools/check_rules.py does not pass:\n" + out[-800:])
    if n >= 1:
        if not (work / "workflow.json").exists():
            return bad + ["workflow.json does not exist"]
        sys.path.insert(0, str(work / "tools"))
        import lint
        problems, _, _ = lint.lint(json.load(open(work / "workflow.json")))
        bad += ["lint: " + p for p in problems]
    if n == 1 and not (work / "design.md").exists():
        bad.append("design.md does not exist")
    return bad
