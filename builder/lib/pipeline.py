"""Phase 0 -> 1 -> 2 in one agent session. After each phase its gate must pass; a failed gate sends the problems back into the same
conversation once. A phase never starts before the previous gate passed."""
import asyncio, json, time

from . import agent, finalize, phases, workdir
from .paths import ROOT, SLOTS
from .trace import Trace


RESERVE = 90          # seconds kept for the final lint, publish and export, so the whole run stays inside --minutes
ARTIFACTS = ["rules.json", "design.json", "workflow.json", "scores.json", "repairs.md", "report.md"]


async def run_phases(work, slot, deadline, trace):
    """Returns True when all three phases passed their gates."""
    async with agent.Session(work, slot, deadline, trace) as session:
        for ph in phases.PHASES:
            n, prompt, seen = ph["n"], ph["prompt"], ""
            for attempt in (1, 2):
                if time.time() > deadline - 20:
                    trace.line("timeout", "no time left for phase %d" % n)
                    return False
                trace.line("phase", "phase %d start (%s), attempt %d, %.1f min left" % (n, ph["skill"], attempt, (deadline - time.time()) / 60))
                seen += " " + await session.send(prompt, n)
                problems = phases.gate(n, work, seen)
                trace.line("gate", "phase %d: %s" % (n, "passed" if not problems else "; ".join(problems)[:300]))
                if not problems:
                    break
                prompt = "The phase %d check failed: %s Fix it and finish the phase." % (n, " ".join(problems))
            else:
                trace.line("FAILED", "phase %d did not pass its check after a retry; stopping" % n)
                return False
    return True


def build(brief, api, slot, cases, minutes, prepare_only=False, fresh=False, dev=False):
    slot = "%s-%s" % (slot, time.strftime("%m%d-%H%M%S")) if fresh else slot
    work = workdir.prepare(brief, api, cases, dev)
    if prepare_only:
        return work, None
    (ROOT / "traces").mkdir(exist_ok=True)
    trace = Trace(ROOT / "traces" / ("%s-%s.log" % (slot, time.strftime("%Y%m%d-%H%M%S"))))
    trace.line("input", "brief=%s tools=%s slot=%s cases=%s dev=%s workdir=%s" % (brief, api, slot, cases, dev, work))
    left_over = [f for f in ARTIFACTS if (work / f).exists()]
    trace.line("clean", "workdir at start: %s; earlier artifacts present: %s" % (sorted(x.name for x in work.iterdir()), left_over or "none"))
    if left_over:
        raise SystemExit("not a clean start: %s" % left_over)
    existed = bool(SLOTS.exists() and slot in json.load(open(SLOTS)))
    trace.line("slot", "%s: %s at the start of the run" % (slot, "already exists on Freya, will be updated in place" if existed else "does not exist yet, will be created"))
    t0 = time.time()
    try:
        asyncio.run(run_phases(work, slot, t0 + minutes * 60 - RESERVE, trace))
    finally:
        result = finalize.finalize(work, slot, trace, existed)
        trace.line("end", "%s, build time %.1f min" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), (time.time() - t0) / 60))
    return work, result
