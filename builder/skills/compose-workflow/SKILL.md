---
name: compose-workflow
description: Phase 1. Build and publish workflow.json from rules.json, following the platform docs.
---

# Phase 1: compose the workflow

Read completely before designing: `docs/workflow-format.md`, `docs/tools-and-code.md`, `examples/base-agent.json`. They are the format: follow them, do not guess. Every value comes from `rules.json` or the tool API.

1. Write `design.md`: one row per live rule, `id | mechanism | where`. Mechanism is structure, code or prompt. gate, calc and state rules may not be prompt; list what you cannot enforce under "not enforced" with the reason.
2. Keep it small: about 600 lines, 4 to 8 nodes.
3. Decisions that matter (the docs explain how):
   - gate: a protected tool exists only in nodes reached through a transition on the bank's own answer
   - facts: one code node computes dates, limits and amounts as text; the model never calculates
   - writes: a pre hook validates and blocks, a post hook records state and adds `what_to_do_next`; `maxRetries` 0
   - counters: `vars`, the engine's `_failure_count`, `{{node.total_turns}}`. To count something the model does, give it a `code_exec` tool to report it: its arguments arrive in `params`, the code writes the next line to say into `vars`, the prompt prints it
   - close: the lifecycle `end_of_call` close tool, outcome and reason from `vars`; hang up with `end_call`
   - every conversation node gets `max_node_turns` and a `max_turn_transition`
4. `python3 tools/lint.py workflow.json`, then `python3 tools/publish.py workflow.json`.

Done when both are clean and publish shows no READBACK line.
