---
name: compose-workflow
description: Phase 1. Build and publish workflow.json from rules.json, following the platform docs.
---

# Phase 1: compose the workflow

Read completely before designing: `docs/workflow-format.md`, `docs/tools-and-code.md`, `examples/base-agent.json`. They are the format: follow them, do not guess. Every value comes from `rules.json` or the tool API.

1. Write `design.json`: `{"rows": [{"rules": ["r1", "r2"], "mechanism": "structure|code|prompt", "where": "<a node, tool or hook of workflow.json>"}]}`, covering every live rule. gate, calc and state rules, and every rule that names a number or a count (once, twice, attempts, times), must be `structure` or `code`, never `prompt`. Phase 1 does not pass otherwise.
2. Keep it small: about 600 lines, 4 to 8 nodes.
3. Decisions that matter (the docs explain how):
   - numbers are flow, not wording: limits, windows, deadlines, amounts and every counter are computed and held in code, and transitions branch on them
   - gate: a protected tool exists only in nodes reached through a transition on the bank's own answer
   - facts: one code node computes dates, limits and amounts as text; the model never calculates
   - writes: a pre hook validates the request and blocks an invalid one by setting `config['url'] = ''` (the platform then answers "Missing required field: url" and sends nothing); never raise. A post hook records state and adds `what_to_do_next`. `maxRetries` 0
   - counters live in `vars`, changed only by code, never by the prompt: the engine's `_failure_count`, `{{node.total_turns}}`, or your own. To count something the model does (an offer made, an attempt, a question asked), give it a `code_exec` report tool: its arguments arrive in `params`, the code updates the counter and writes the next allowed line into `vars`, the prompt prints it, and a transition branches on the counter
   - a rule that limits what the agent may offer or say (attempts, offers, asks) is enforced by code owning the line: the report tool returns the exact next line, or "no further offer", the prompt says it verbatim, and the model never composes the offer itself
   - close: the lifecycle `end_of_call` close tool, outcome and reason from `vars`; hang up with `end_call`
   - every conversation node gets `max_node_turns` and a `max_turn_transition`
4. `python3 tools/lint.py workflow.json`, then `python3 tools/publish.py workflow.json`.

Done when both are clean, publish shows no READBACK line, and design.json is complete.
