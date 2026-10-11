"""After the phases: the harness, not the agent, lints, publishes into the slot, exports and copies the evidence."""
import json, shutil, sys

from .paths import BUILDER, KIT, ROOT, SLOTS
from .workdir import sealed_dir

EVIDENCE = ["inputs.json", "rules.json", "design.json", "repairs.md", "report.md", "scores.json"]


def finalize(work, slot, trace):
    sys.path.insert(0, str(KIT)); sys.path.insert(0, str(BUILDER / "tools"))
    import freya, lint
    if not (work / "workflow.json").exists():
        trace.line("FAILED", "no workflow.json was produced")
        return None
    wf = json.load(open(work / "workflow.json"))
    base = json.load(open(work / json.load(open(work / "inputs.json"))["tools"]))["servers"][0]["url"].rstrip("/")
    bad, _, lines = lint.lint(wf, base)
    trace.line("lint", "%d lines, %d nodes, %s" % (lines, len(wf["nodes"]), "clean" if not bad else "FAILED: " + "; ".join(bad)[:300]))
    if bad:
        return None
    known = json.load(open(SLOTS)).get(slot) if SLOTS.exists() else None
    r = freya.save_workflow(slot, wf, state_file=str(SLOTS))
    trace.line("freya", "slot %s: %s" % (slot, "updated in place (an earlier build of this slot existed)" if known else "created new, first build of this slot"))
    out = ROOT / "submission"
    shutil.rmtree(out / slot, ignore_errors=True)       # no stale evidence from an earlier run
    (out / slot / "results").mkdir(parents=True, exist_ok=True)
    freya.export_workflow(r["workflow_id"], str(out / (slot + ".workflow.json")))
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
