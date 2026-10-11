---
name: compose-workflow
description: Phase 1. Build and publish workflow.json from rules.json, following the platform docs.
---

# Phase 1: compose the workflow

Read completely before designing: `docs/workflow-format.md`, `docs/tools-and-code.md`, `examples/base-agent.json`. They are the format: follow them, do not guess. Every value comes from `rules.json` or the tool API. The model in a node sees only that node's prompt, so a node is the policy that is in force.

1. Write `design.json`: `{"rows": [{"rules": ["r1", "r2"], "mechanism": "structure|code|prompt", "where": "<a node, tool or hook of workflow.json>"}]}`, covering every live rule. By `kind`: gate, limit and allowed_set rules, and every rule that names a number or a count, are `structure` or `code`, never `prompt`. A `wording` rule puts its `wording` into the workflow exactly as the brief has it. A prompt row names its node (or system_prompt). Phase 1 does not pass otherwise.
2. Keep it small: at most 1000 lines, 4 to 8 nodes, at most 8 prompt-only rules per node. More rules than that: split the node by state, or settle them in code and show the model the conclusion.
3. Decisions that matter (the docs explain how):
   - numbers are flow, not wording: limits, windows, deadlines, amounts and every counter are computed and held in code, and transitions branch on them
   - interdependent rules are settled in code: one code node derives the situation (stage, allowed set, deadline, attempts left) as variables; the prompt shows these facts, never the interplay of rules
   - each conversation node's `task_message` is its role, the situation facts (`{{vars}}`) and the policy of that node only: what may and may not be done, what must be conveyed and before what. Context and policy, not a script. The platform rejects `loop_prompt`: put everything in `task_message`. Rules that hold everywhere are a few lines in `system_prompt`
   - gate: a protected tool exists only in nodes reached through a transition on the bank's own answer
   - customer intent enters through `extraction_schema` enum slots and transitions on them. A tool the model calls reports facts the code needs; its name and arguments never state an outcome the code then decides
   - writes: a pre hook on a tool the model calls validates the request and blocks an invalid one by setting `config['url'] = ''` (the platform then answers "Missing required field: url" and sends nothing); never raise. Use it only there. A node that runs on entry (`pre_actions`) always makes its call: a node that is sometimes not needed is skipped by a transition on a variable set before it. A post hook records state and returns facts and what is now allowed or forbidden, not a sentence to speak. `maxRetries` 0
   - optional actions (notes, a transfer, a callback) are tools of one conversation node, or `pre_actions` of a node reached only when needed; never a chain of three or more passthrough nodes. Lint enforces this
   - a counter or gate that decides an outcome rests on the bank's own answers, the engine's `_failure_count`, or an explicit tool call by the model with a closed set of values. An extraction slot is re-read from the last messages every turn: use it to fork routing, with an "unclear, stay" default, never as the count of what the customer did
   - counters live in `vars`, changed only by code, never by the prompt: the engine's `_failure_count`, `{{node.total_turns}}`, or your own
   - a rule that limits what the agent may offer (attempts, offers, asks): code computes the allowed set and what is left, the prompt shows it as a constraint ("allowed: ...; nothing else"), a transition ends the stage when none is left
   - close: the lifecycle `end_of_call` close tool, outcome and reason from `vars`; hang up with `end_call`
   - every conversation node gets `max_node_turns` (sized from the longest real step, at most 30) and a `max_turn_transition`: a stuck loop must end
   - a read-back or confirmation shows what the customer just said. A value the customer gave and the code did not capture is asked for again; it is never replaced by an earlier value or a default. A date the customer says in words ("the twenty sixth", "next Friday") is declared `type: "date"` in the extraction schema, and the code checks that it arrived
4. `python3 tools/lint.py workflow.json`, `python3 tools/check_design.py`, then `python3 tools/publish.py workflow.json`. A FAIL is a must: the workflow is not tested until it is fixed, and the phase gate runs the same checks. A WARN is a reason to look: fix it, or leave one line in `design.json` under `warnings` saying why it stays.

Done when all three are clean, publish shows no READBACK line, and design.json is complete.
