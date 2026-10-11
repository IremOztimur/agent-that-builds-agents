"""One Claude Agent SDK session for one phase, in the agent's working folder, with the trace of what it did."""
import asyncio, os, time

from .paths import BUILDER, SLOTS
from .workdir import SKILLS, sealed_dir


async def run_phase(work, slot, phase, prompt, deadline, trace):
    """Runs the phase until the agent stops or the clock ends. Returns what the agent read (paths and commands, lower-case)."""
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, ToolUseBlock, query
    model = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
    options = ClaudeAgentOptions(
        cwd=work, model=model, skills=SKILLS, setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], permission_mode="dontAsk", max_turns=80,
        env={"BASH_DEFAULT_TIMEOUT_MS": "900000", "BASH_MAX_TIMEOUT_MS": "1200000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
             "BUILDER_SLOT": slot, "BUILDER_SLOT_STATE": str(SLOTS), "BUILDER_DEADLINE": str(deadline), "BUILDER_SEALED": str(sealed_dir(work))})
    seen = []

    async def go():
        async for m in query(prompt=prompt, options=options):
            if isinstance(m, AssistantMessage):
                uses = [b for b in m.content if isinstance(b, ToolUseBlock)]
                texts = [b.text for b in m.content if isinstance(b, TextBlock)]
                for b in uses:
                    seen.append(" ".join(str(v) for v in b.input.values()).lower())
                    if b.name == "Bash" and any(k in str(b.input.get("command", "")) for k in ("practice.py", "check_rules", "lint.py", "publish.py", "run_code")):
                        trace.line("selftest", str(b.input.get("command"))[:200])
                what = ", ".join("%s %s" % (b.name, str(b.input.get("skill") or b.input.get("file_path") or b.input.get("command") or "")[:70]) for b in uses)
                trace.line("model", "%s: %s" % (getattr(m, "model", model), what or (texts[0][:100] if texts else "")))
            elif isinstance(m, ResultMessage):
                trace.line("phase", "phase %d done: %d turns, %.0f s, $%.2f" % (phase, m.num_turns, m.duration_ms / 1000, m.total_cost_usd or 0))

    try:
        await asyncio.wait_for(go(), timeout=max(30, deadline - time.time()))
    except asyncio.TimeoutError:
        trace.line("timeout", "the clock ran out during phase %d" % phase)
    return " ".join(seen)
