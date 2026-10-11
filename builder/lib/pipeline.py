"""Phase 0 -> 1 -> 2 in order. After each phase its gate must pass; a failed gate gives the agent one retry of the same phase."""
import asyncio, time

from . import agent, finalize, phases, workdir
from .paths import ROOT
from .trace import Trace


def run_phases(work, slot, deadline, trace):
    """Returns True when all three phases passed their gates."""
    for ph in phases.PHASES:
        n, prompt = ph["n"], ph["prompt"]
        for attempt in (1, 2):
            if time.time() > deadline - 20:
                trace.line("timeout", "no time left for phase %d" % n)
                return False
            trace.line("phase", "phase %d start (%s), attempt %d, %.1f min left" % (n, ph["skill"], attempt, (deadline - time.time()) / 60))
            seen = asyncio.run(agent.run_phase(work, slot, n, prompt, deadline, trace))
            problems = phases.gate(n, work, seen)
            trace.line("gate", "phase %d: %s" % (n, "passed" if not problems else "; ".join(problems)[:300]))
            if not problems:
                break
            prompt = ph["prompt"] + " The gate failed: " + " ".join(problems)
        else:
            trace.line("FAILED", "phase %d gate did not pass after a retry; stopping" % n)
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
        run_phases(work, slot, time.time() + minutes * 60, trace)
    finally:
        result = finalize.finalize(work, slot, trace)
        trace.line("end", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    return work, result
