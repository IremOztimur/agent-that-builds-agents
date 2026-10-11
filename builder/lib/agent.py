"""One Claude Agent SDK session for the whole build. The harness sends the phase prompts one after another into the same
conversation, so the agent keeps what it learned in earlier phases; code checks each phase before the next prompt."""
import asyncio, os, re, time

from .paths import SLOTS
from .workdir import SKILLS, sealed_dir


ABS = re.compile(r"(?<![\w.])/(?:Users|private|var|tmp|home|opt|etc)/[^\s'\"`;|&)<>]+")

SELFTEST = re.compile(r"python3?\s+tools/(practice|check_rules|check_expectations|check_workflow|check_design|lint|publish|run_code)\.py[^\n;&|]*")


class Session:
    def __init__(self, work, slot, deadline, trace):
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        self.model = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
        self.deadline, self.trace = deadline, trace
        self.home = str(work.resolve()), str(work)
        self.client = ClaudeSDKClient(options=ClaudeAgentOptions(
            cwd=work, model=self.model, skills=SKILLS, setting_sources=["project"],
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], permission_mode="dontAsk", max_turns=200,
            env={"BASH_DEFAULT_TIMEOUT_MS": "900000", "BASH_MAX_TIMEOUT_MS": "1200000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
                 "BUILDER_SLOT": slot, "BUILDER_SLOT_STATE": str(SLOTS), "BUILDER_DEADLINE": str(deadline), "BUILDER_SEALED": str(sealed_dir(work)), "BUILDER_TRACE": str(trace.path)}))

    async def __aenter__(self):
        await self.client.connect()
        self.trace.line("model", "builder model %s, one session for all phases" % self.model)
        return self

    async def __aexit__(self, *exc):
        await self.client.disconnect()

    async def send(self, prompt, phase):
        """Sends one prompt and waits until the agent stops or the clock ends. Returns what it read (paths and commands, lower-case)."""
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage
        seen, tests = [], {}

        async def consume():
            async for m in self.client.receive_response():
                if isinstance(m, AssistantMessage):
                    uses = [b for b in m.content if isinstance(b, ToolUseBlock)]
                    texts = [b.text for b in m.content if isinstance(b, TextBlock)]
                    for b in uses:
                        text = " ".join(str(v) for v in b.input.values())
                        seen.append(text.lower())
                        for path in ABS.findall(text):
                            if not path.startswith(self.home) and "/.claude/projects/" not in path and not path.startswith(("/tmp/", "/dev/")):
                                self.trace.line("OUTSIDE", "%s reached outside its folder: %s" % (b.name, path[:160]))
                        found = [f.group(0).strip()[:140] for f in SELFTEST.finditer(str(b.input.get("command", "")))] if b.name == "Bash" else []
                        if found:
                            tests[b.id] = " && ".join(found)          # one command can chain several tools: every one is named, the result belongs to all of them
                            for f in found:
                                self.trace.line("selftest", "started: " + f)
                    what = ", ".join("%s %s" % (b.name, str(b.input.get("skill") or b.input.get("file_path") or b.input.get("command") or "")[:70]) for b in uses)
                    self.trace.line("model", "%s: %s" % (getattr(m, "model", self.model), what or (texts[0][:100] if texts else "")))
                elif isinstance(m, UserMessage) and isinstance(m.content, list):
                    for b in m.content:
                        if isinstance(b, ToolResultBlock) and b.tool_use_id in tests:
                            out = b.content if isinstance(b.content, str) else " ".join(str(x.get("text", "")) for x in (b.content or []) if isinstance(x, dict))
                            tail = " ".join(out.split())[-420:]
                            self.trace.line("selftest", "result of %s -> %s%s" % (tests.pop(b.tool_use_id), "ERROR " if b.is_error else "", tail))
                elif isinstance(m, ResultMessage):
                    self.trace.line("phase", "phase %d turn finished: %d turns so far, $%.2f" % (phase, m.num_turns, m.total_cost_usd or 0))

        self.trace.line("model", "%s asked: %s" % (self.model, prompt[:200]))
        await self.client.query(prompt)
        try:
            await asyncio.wait_for(consume(), timeout=max(30, self.deadline - time.time()))
        except asyncio.TimeoutError:
            await self.client.interrupt()
            self.trace.line("timeout", "the clock ran out during phase %d" % phase)
        return " ".join(seen)
