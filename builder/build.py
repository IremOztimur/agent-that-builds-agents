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
EVIDENCE = ["inputs.json", "rules.json", "design.md", "repairs.md", "report.md", "scores.json"]

PROMPT = """Build a phone agent for the bank brief in {brief_file} ({brief_lines} lines), using the tool API in {tools_file}.
Both names are also in inputs.json. The brief may be a specification, a mail, a memo, notes or a transcript; read all of it.
Use the skills in this order: read-brief, compose-workflow, test-and-repair. Work only with the files in this folder.
The practice customers for this brief are run with tools/practice.py (brief {cases}); they show what happened, not what was expected. The final workflow must be in
workflow.json and published with tools/publish.py. You have {minutes} minutes in total (tools/clock.py shows what is left);
do not start a step you cannot finish. Finish with one line: the workflow_id, the agent_id, and how many customers passed."""


def read_text(path):
    """The brief as text, whatever it is called. A mail, memo, notes or specification; .docx is unpacked. Fails loudly."""
    p = pathlib.Path(path)
    if not p.is_file():
        sys.exit("brief not found: %s" % path)
    data = p.read_bytes()
    if p.suffix.lower() == ".docx":
        import re, zipfile
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", "ignore")
        text = re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml))
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            sys.exit("the brief %s is not UTF-8 text; convert it to text first (a PDF cannot be read as it is)" % path)
    if not text.strip():
        sys.exit("the brief %s is empty" % path)
    return text


def prepare(brief, api, slot, cases):
    work = pathlib.Path(tempfile.mkdtemp(prefix="builder-"))
    text = read_text(brief)
    spec = json.load(open(api))                       # the tool API file, any name; must be an OpenAPI JSON document
    if not spec.get("servers") or not spec.get("paths"):
        sys.exit("the tool API file %s has no servers or paths" % api)
    (work / "input").mkdir()
    bname = pathlib.Path(brief).name + (".txt" if pathlib.Path(brief).suffix.lower() == ".docx" else "")
    (work / "input" / bname).write_text(text)
    shutil.copy(api, work / "input" / pathlib.Path(api).name)
    (work / "inputs.json").write_text(json.dumps({"brief": "input/" + bname, "tools": "input/" + pathlib.Path(api).name, "brief_lines": len(text.splitlines())}))
    (work / "docs").mkdir()
    for d in ("workflow-format.md", "tools-and-code.md", "api.md"):
        shutil.copy(KIT / "docs" / d, work / "docs" / d)
    (work / "examples").mkdir()
    shutil.copy(KIT / "examples" / "base-agent.json", work / "examples" / "base-agent.json")
    shutil.copy(KIT / "freya.py", work / "freya.py")
    shutil.copytree(BUILDER / "tools", work / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    # The practice customers live in a sealed folder outside the workdir: the agent runs them through tools/practice.py
    # and sees what happened, never the expected values or the customer scripts.
    sealed = pathlib.Path(tempfile.mkdtemp(prefix="sealed-"))
    (sealed / "tools").mkdir(); (sealed / "results").mkdir()
    for f in ("run_cases.py", "score.py"):
        shutil.copy(KIT / "tools" / f, sealed / "tools" / f)
    shutil.copy(KIT / "freya.py", sealed / "freya.py")
    shutil.copy(KIT / "public-test-set.json", sealed / "public-test-set.json")
    personas = BUILDER / ".personas.json"           # persona ids are reused across builds so the workspace does not fill up
    shutil.copy(personas if personas.exists() else KIT / ".personas.json", sealed / ".personas.json")
    (work / "versions").mkdir()
    (work / ".sealed").write_text(str(sealed))
    for s in SKILLS:
        shutil.copytree(BUILDER / "skills" / s, work / ".claude" / "skills" / s)
    return work


def names(work):
    m = json.load(open(work / "inputs.json"))
    return {"brief_file": m["brief"], "tools_file": m["tools"], "brief_lines": m["brief_lines"]}


def sealed_dir(work):
    return pathlib.Path((work / ".sealed").read_text())


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
             "BUILDER_SLOT": slot, "BUILDER_SLOT_STATE": str(BUILDER / ".slots.json"), "BUILDER_DEADLINE": str(time.time() + minutes * 60), "BUILDER_SEALED": str(sealed_dir(work))})
    trace.line("model", "builder model %s" % model)

    async def go():
        async for m in query(prompt=PROMPT.format(minutes=minutes, cases=cases, **names(work)), options=options):
            if isinstance(m, AssistantMessage):
                uses = [b for b in m.content if isinstance(b, ToolUseBlock)]
                texts = [b.text for b in m.content if isinstance(b, TextBlock)]
                purpose = ", ".join("%s %s" % (b.name, str(b.input.get("command") or b.input.get("file_path") or b.input.get("skill") or "")[:70]) for b in uses) or (texts[0][:100] if texts else "")
                trace.line("model", "%s: %s" % (getattr(m, "model", model), purpose))
                for b in uses:
                    cmd = str(b.input.get("command", ""))
                    if any(k in cmd for k in ("practice.py", "check_rules", "lint.py", "publish.py", "run_code")):
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
    base = json.load(open(work / json.load(open(work / "inputs.json"))["tools"]))["servers"][0]["url"].rstrip("/")
    bad, warn, lines = lint.lint(wf, base)
    trace.line("lint", "%d lines, %d nodes, %s" % (lines, len(wf["nodes"]), "clean" if not bad else "FAILED: " + "; ".join(bad)[:300]))
    if bad:
        return None
    r = freya.save_workflow(slot, wf, state_file=str(BUILDER / ".slots.json"))
    out = ROOT / "submission"
    (out / slot).mkdir(parents=True, exist_ok=True)
    freya.export_workflow(r["workflow_id"], str(out / (slot + ".workflow.json")))
    (out / slot / "results").mkdir(exist_ok=True)
    for f in (sealed_dir(work) / "results").glob("*.json"):
        shutil.copy(f, out / slot / "results" / f.name)
    for e in EVIDENCE:
        if (work / e).exists():
            shutil.copy(work / e, out / slot / e)
    if (sealed_dir(work) / ".personas.json").exists():
        shutil.copy(sealed_dir(work) / ".personas.json", BUILDER / ".personas.json")
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
