"""Phase 0 -> 1 -> 2 in one agent session. After each phase its gate must pass; a failed gate sends the problems back into the same
conversation once. A phase never starts before the previous gate passed."""
import asyncio, time

from . import agent, finalize, phases, workdir
from .paths import ROOT
from .trace import Trace


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


def build(brief, api, slot, cases, minutes, prepare_only=False):
    work = workdir.prepare(brief, api, cases)
    if prepare_only:
        return work, None
    (ROOT / "traces").mkdir(exist_ok=True)
    trace = Trace(ROOT / "traces" / ("%s-%s.log" % (slot, time.strftime("%Y%m%d-%H%M%S"))))
    trace.line("input", "brief=%s tools=%s slot=%s cases=%s workdir=%s" % (brief, api, slot, cases, work))
    try:
        asyncio.run(run_phases(work, slot, time.time() + minutes * 60, trace))
    finally:
        result = finalize.finalize(work, slot, trace)
        trace.line("end", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    return work, result
