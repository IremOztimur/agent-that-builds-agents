# Format rules

What the platform does with a workflow. Build to these while you design; `tools/check_workflow.py` checks every one and names it by id. F = must (the workflow is not tested until it is fixed), W = look at it, fix it or say in `design.json` under `warnings` why it stays. Sources: `docs/workflow-format.md` (WF), `docs/tools-and-code.md` (TC).

| Id | Rule | Source |
|---|---|---|
| F1 | No `null` anywhere. Leave an optional field out or use `""` | WF top-level keys |
| F2 | `tools` only on `conversation` nodes, `pre_actions` only on `api_request` and `code` nodes. Elsewhere the platform drops them without an error | WF node types |
| F3 | A passthrough node ends its `transitions` with an `always` transition, or the call deadlocks | WF passthrough |
| F4 | Every transition and `max_turn_transition` target exists, and every node can reach an `end_call` node | WF design rules |
| F5 | A top-level condition group is `"logic": "or"`; nest `and` inside it | WF condition shapes |
| F6 | Every extraction variable sets `min_confidence` (the default 0.95 silently discards values) | WF extraction |
| F7 | A custom `extraction_prompt` replaces the whole template: it must contain `{{extractor.speech}}`, `{{extractor.conversation.last-10}}`, `{{extractor.type_preamble}}`, `{{extractor.variables_list}}` | WF extraction |
| F8 | `response_mapping` paths start with `data.` | TC response_mapping |
| F9 | Code reads and writes `vars`, has no `{{ }}`, and compiles. Booleans arrive as strings | TC code nodes |
| F10 | Calls go only to the tool API host. Parameters bake `default`, never `const` | TC tools |
| F11 | Every conversation node has `max_node_turns` (30 at most) and a `max_turn_transition`; without the target the cap does nothing | WF limits |
| F12 | No `loop_prompt`: the platform rejects it ("Unrecognized key") although the docs list it | seen in a dry run |
| F13 | An `end_call` node has a `terminal`; the farewell is its `spoken_message` and `on_enter` is `silent`, otherwise the call hangs up silently | WF end-call nodes |
| F14 | A node that runs on entry (`pre_actions`) always makes its call. A node that is sometimes not needed is skipped by a transition on a variable. Never blank the url there: the platform logs a failed `api_call` on every pass | TC pre_actions vs tools |
| W1 | Optional actions (notes, transfer, callback) are tools of one conversation node, not a chain of passthrough nodes | TC pre_actions vs tools |
| W2 | Dates are extracted with `type: "date"` (a string gets no date anchor) | WF extraction |
| W3 | Test a boolean as both `"true"` and `"True"`, or use a string value | WF booleans |
| W4 | A tool description says when to CALL it; otherwise the model talks about the action instead | TC tool descriptions |
| W5 | `context_variables` is dropped on save; put the values in the prompt with `{{var}}` | WF context variables |
| W6 | A `task_message` does not name nodes or routing; the model narrates steps that have not happened | WF prompts |
| W7 | Size: about 600 lines, turn caps above 20 run long | WF limits |

Also, from the docs: deterministic conditions go before `matches_intent`; fork on an extracted enum with `equals`; a node without tools says no tool call is allowed in this turn; keep dialogue in `task_message`, routing in `transitions`, data capture in `extraction_schema`.
