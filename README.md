# agent-that-builds-agents

A builder for the Freya x Y Combinator "Build the Builder" hackathon. It reads a bank's documents, builds a phone agent (a workflow) on
Freya, tests it against simulated customers and repairs it. No manual step.

    python3 builder/build.py <case folder> <mock url> 2>&1 | tee traces/final.log             the final: a folder of the bank's documents and your mock
    python3 builder/build.py <brief file> <tool API file> [--slot NAME] [--cases A|B|AB] [--minutes 30] [--fresh] [--dev]   development, on the practice briefs

Needs `FREYA_API_KEY` and `FREYA_BANK_TEAM_KEY` (copy `builder/kit/env.template` to `env.sh`, fill it in, `source env.sh`), `pip install claude-agent-sdk`,
and a Claude login or `ANTHROPIC_API_KEY`. `--dev` scores the practice customers against the kit's public expected values (development only);
without it the builder's own expectations, derived from the brief, decide.

## How it works

One Claude Agent SDK session works through three phases in order. A deterministic gate checks each phase before the next one starts.

| Phase | Skill | Gate |
|---|---|---|
| 0 read the brief | `builder/skills/read-brief` | `rules.json` (every rule quoted verbatim from the brief, with kind and situation) and `expectations.json` (what each test customer must leave in the bank) pass `check_rules` and `check_expectations` |
| 1 compose the workflow | `builder/skills/compose-workflow` (+ `format-rules.md`) | `check_workflow.py`: format rules F/W from the platform docs, design check (every rule has a mechanism, hard rules are code or structure, mandated wording is present), platform dry run; then a live chat check |
| 2 test and repair | `builder/skills/test-and-repair` | `practice.py` rounds (mixed talking styles), stop rule, best measured version ships |

In a case-folder run the documents (Markdown, text, Word, Excel, PDF; images are read by the agent) become one `corpus.md`, the agent writes `topics.json` from the test customers, and
`practice.py` plays them against the mock and scores the mock's ledger (`GET /_ledger/<id>`) with the agent's own expectations.

The harness (`builder/lib`) prepares a clean working folder, runs the phases, publishes, exports and writes the trace. Facts it enforces:
numbers and counters are code, never prompt; the agent never sees the expected values; a repaired workflow is measured before it can ship.

## Layout

    builder/build.py      entry point
    builder/lib/          harness: intake, workdir, phases and gates, agent session, pipeline, finalize, trace
    builder/tools/        tools the agent runs in its folder: lint, check_*, publish, practice (the sealed test runner), stop rule, styles
    builder/skills/       the three skills
    builder/kit/          the hackathon kit files the builder needs (freya.py, platform docs, base agent, public practice set), vendored
    builder/tests/        offline tests: python3 builder/tests/test_<name>.py (no platform needed)
    mock/                 a generic Cloudflare Workers mock of the bank (routing, consistent per-customer ledger); fill in handlers.js from the service contract
    dev/                  development scripts and fixtures, not part of the builder

Runs write their trace to `traces/` and their exports to `submission/`; both are ignored. For the final submission:
`git add -f submission/<name>.workflow.json traces/<name>.log`.
