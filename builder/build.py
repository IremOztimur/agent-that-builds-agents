"""The builder: reads a bank brief and its tool API file, creates the phone agent on Freya. No manual step.

    python3 builder/build.py <brief.md> <tools.json> [--slot NAME] [--cases A|B] [--minutes 27] [--prepare-only]

One Claude Agent SDK session works in a clean temporary folder that holds only the brief, the tool API file, the platform
docs, the example agent, the practice customers of the brief (A or B) and the helper tools. Three skills (read-brief, compose-workflow, test-and-repair) guide it.
The harness, not the agent, does the final lint, publish into the slot, export and trace. Needs FREYA_API_KEY and a
Claude login (or ANTHROPIC_API_KEY); BUILDER_MODEL picks the model.
"""
import asyncio, dataclasses, json, os, pathlib, shutil, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILDER = ROOT / "builder"
KIT = ROOT / "build-the-builder_pack"
SKILLS = ["read-brief", "compose-workflow", "test-and-repair"]
EVIDENCE = ["rules.json", "design.md", "repairs.md", "report.md", "scores.json"]

PROMPT = """Build a phone agent for the bank brief in brief.md, using the tool API in tools.json.
Use the skills in this order: read-brief, compose-workflow, test-and-repair. Work only with the files in this folder.
The practice customers for this brief are the cases of brief {cases} in public-test-set.json. The final workflow must be in
workflow.json and published with tools/publish.py. You have {minutes} minutes in total (tools/clock.py shows what is left);
do not start a step you cannot finish. Finish with one line: the workflow_id, the agent_id, and how many customers passed."""


def prepare(brief, api, slot, cases):
    work = pathlib.Path(tempfile.mkdtemp(prefix="builder-"))
    shutil.copy(brief, work / "brief.md")
    shutil.copy(api, work / "tools.json")
    (work / "docs").mkdir()
    for d in ("workflow-format.md", "tools-and-code.md", "api.md"):
        shutil.copy(KIT / "docs" / d, work / "docs" / d)
    (work / "examples").mkdir()
    shutil.copy(KIT / "examples" / "base-agent.json", work / "examples" / "base-agent.json")
    shutil.copy(KIT / "freya.py", work / "freya.py")
    shutil.copytree(BUILDER / "tools", work / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("run_cases.py", "score.py"):
        shutil.copy(KIT / "tools" / f, work / "tools" / f)
    shutil.copy(KIT / "public-test-set.json", work / "public-test-set.json")
    personas = BUILDER / ".personas.json"           # persona ids are reused across builds so the workspace does not fill up
    shutil.copy(personas if personas.exists() else KIT / ".personas.json", work / ".personas.json")
    for d in ("versions", "results"):
        (work / d).mkdir()
    for s in SKILLS:
        shutil.copytree(BUILDER / "skills" / s, work / ".claude" / "skills" / s)
    return work


class Trace:
    def __init__(self, path):
        self.f = path.open("w")
        self.line("start", time.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def line(self, kind, text):
        self.f.write("%s | %-8s | %s\n" % (time.strftime("%H:%M:%S"), kind, text.replace("\n", " ")[:400]))
        self.f.flush()


async def run_agent(work, slot, minutes, cases, trace):
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, ToolUseBlock, query
    model = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
    options = ClaudeAgentOptions(
        cwd=work, model=model, skills=SKILLS, setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], permission_mode="dontAsk", max_turns=150,
        env={"BASH_DEFAULT_TIMEOUT_MS": "900000", "BASH_MAX_TIMEOUT_MS": "1200000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
             "BUILDER_SLOT": slot, "BUILDER_SLOT_STATE": str(BUILDER / ".slots.json"), "BUILDER_DEADLINE": str(time.time() + minutes * 60)})
    trace.line("model", "builder model %s" % model)

    async def go():
        async for m in query(prompt=PROMPT.format(minutes=minutes, cases=cases), options=options):
            if isinstance(m, AssistantMessage):
                uses = [b for b in m.content if isinstance(b, ToolUseBlock)]
                texts = [b.text for b in m.content if isinstance(b, TextBlock)]
                purpose = ", ".join("%s %s" % (b.name, str(b.input.get("command") or b.input.get("file_path") or b.input.get("skill") or "")[:70]) for b in uses) or (texts[0][:100] if texts else "")
                trace.line("model", "%s: %s" % (getattr(m, "model", model), purpose))
                for b in uses:
                    cmd = str(b.input.get("command", ""))
                    if any(k in cmd for k in ("run_cases", "show_failures", "check_rules", "lint.py", "publish.py", "run_code")):
                        trace.line("selftest", cmd[:200])
            elif isinstance(m, ResultMessage):
                trace.line("done", "%d turns, %.0f s, $%.2f" % (m.num_turns, m.duration_ms / 1000, m.total_cost_usd or 0))
    try:
        await asyncio.wait_for(go(), timeout=minutes * 60)
    except asyncio.TimeoutError:
        trace.line("timeout", "builder clock of %d minutes ran out; finalising what exists" % minutes)


def finalize(work, slot, trace):
    sys.path.insert(0, str(KIT)); sys.path.insert(0, str(BUILDER / "tools"))
    import freya, lint
    wf_path = work / "workflow.json"
    if not wf_path.exists():
        trace.line("FAILED", "the builder produced no workflow.json")
        return None
    wf = json.load(open(wf_path))
    base = json.load(open(work / "tools.json"))["servers"][0]["url"].rstrip("/")
    bad, warn, lines = lint.lint(wf, base)
    trace.line("lint", "%d lines, %d nodes, %s" % (lines, len(wf["nodes"]), "clean" if not bad else "FAILED: " + "; ".join(bad)[:300]))
    if bad:
        return None
    r = freya.save_workflow(slot, wf, state_file=str(BUILDER / ".slots.json"))
    out = ROOT / "submission"
    (out / slot).mkdir(parents=True, exist_ok=True)
    freya.export_workflow(r["workflow_id"], str(out / (slot + ".workflow.json")))
    for e in EVIDENCE:
        if (work / e).exists():
            shutil.copy(work / e, out / slot / e)
    if (work / ".personas.json").exists():
        shutil.copy(work / ".personas.json", BUILDER / ".personas.json")
    trace.line("freya", "workflow_id=%s agent_id=%s nodes=%d tools=%d" % (
        r["workflow_id"], r["agent_id"], len(wf["nodes"]), sum(len(n.get("tools", [])) for n in wf["nodes"].values())))
    return r


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    brief, api = argv[0], argv[1]
    opt = {argv[i]: argv[i + 1] for i in range(2, len(argv) - 1) if argv[i].startswith("--")}
    slot = opt.get("--slot") or pathlib.Path(brief).stem
    minutes = int(opt.get("--minutes", 27))
    cases = opt.get("--cases", "A")
    work = prepare(brief, api, slot, cases)
    if "--prepare-only" in argv:
        print(work)
        return
    (ROOT / "traces").mkdir(exist_ok=True)
    trace = Trace(ROOT / "traces" / ("%s-%s.log" % (slot, time.strftime("%Y%m%d-%H%M%S"))))
    trace.line("input", "brief=%s tools=%s slot=%s workdir=%s" % (brief, api, slot, work))
    try:
        asyncio.run(run_agent(work, slot, minutes, cases, trace))
    finally:
        r = finalize(work, slot, trace)
        trace.line("end", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        print(json.dumps(r or {"failed": True}))


if __name__ == "__main__":
    main(sys.argv[1:])
