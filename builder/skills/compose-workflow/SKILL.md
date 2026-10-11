---
name: compose-workflow
description: Design and write the Freya phone-agent workflow (workflow.json) from rules.json, following the platform docs, enforcing every hard rule by structure or code, and mapping each rule to a mechanism in design.md.
---

# Compose the workflow

Read in full before designing: `docs/workflow-format.md` and `docs/tools-and-code.md` (the format; follow them exactly), and `examples/base-agent.json` (a working agent: two nodes, tools, a lifecycle close). Read no other workflow. Every value (dates, limits, outcome names, queue names, phrases) comes from `rules.json` or the tool API file, never from memory.

## 1. design.md first

One row per live rule (decided, proposed, or unresolved-with-the-stricter-reading): `rule id | mechanism | where`.
Mechanisms: `structure` (a tool is absent from every node where it must not be callable; node order; a transition on the bank's own answer), `code` (a code node or hook computes, validates or counts), `prompt` (wording only).
Rules of class gate, calc and state may not use `prompt`. If you cannot enforce one, list it under "not enforced" with the reason; do not hide it in prompt text.

## 2. Shape

The smallest workflow that works: about 600 lines pretty-printed (`tools/lint.py` reports it), usually 4 to 8 nodes. Typical stages: who is on the line, identity, one code node for facts, the conversation node that holds the tools, a closing path. Keep related optional actions together in one conversation node with several tools. Do not make a node per rule.

## 3. How a turn runs (the model of the platform)

After each user message three separate model calls run: extraction (fills `extraction_schema` variables), routing (reads only the transitions, never your `task_message`), dialogue (reads `system_prompt`, `task_message`, history and the node's `tools`). So routing text in a prompt does nothing; routing lives in `transitions`. The dialogue model can call only the tools listed in the current node. Variable conditions are evaluated in code; `matches_intent` costs a model call and is the least reliable. Routing runs again after a tool result and a transition on a mapped variable fires in the same turn. If nothing matches, the agent stays in the node: end lists with a sensible `always`.

## 4. Patterns

- **Gate by structure.** List a protected tool only in a node reachable through a transition whose condition reads the bank's own answer: `response_mapping` (tool level for `tools`, node level for `pre_actions`, paths start with `data.`) or the automatic key `<tool>_response.data.<field>`. Test both "true" and "True", or map to a string. Never gate on what the customer said, on an extracted variable, or on `matches_intent`.
- **Facts in code.** After the data call, a passthrough `code` node computes everything the prompts need (dates from `now`, deadlines, allowed-day tables, limits, finished amounts as text) into `vars`; prompts print `{{var}}`. The model never calculates dates or limits. Write dates as ISO strings. Write a fallback for every variable a prompt reads (an unset one shows as the literal `{{name}}`).
- **Write guard.** Every tool that writes gets a `pre_process_code` hook (`vars`, `config`) that checks the request against the computed limits and blocks an invalid one by setting `config['url'] = ''`. A `post_process_code` hook (`result` is the envelope; the bank's body is `result['data']`) writes a state string to `vars` and adds `what_to_do_next` to `result['data']`, which tells the model what to say. Hooks exist only on `api_call` tools. Wrap them in try/except. Writes get `maxRetries` 0 (a retried write can record twice); reads may retry.
- **Counters.** Attempts, "only once" offers and per-item progress live in `vars` (hooks or code nodes). The engine also keeps `<tool>_success_count` / `<tool>_failure_count` (and `<node>_...` for `pre_actions` nodes) and `{{<node>.total_turns}}`. Use them in transitions. A prompt alone does not count reliably.
- **Closing.** The bank's close call must be the last tool call, exactly once. The kit's base agent does it with a workflow-level lifecycle tool (`config.alwaysRunsAt: ["end_of_call"]`, top-level `tools`), whose unresolved parameters are filled at the end; a hook can set outcome and reason from `vars`. Ending the call is separate: an `end_call` node (farewell comes from the terminal's `spoken_message`, not `on_enter`; `endedReason` is the terminal's function name) or the `end_call` tool. Check what the stored workflow and a practice run show.
- **Fixed sentences.** The opening and any required sentence are `on_enter` `tts` text, with `on_enter_first_entry_only` where a node can be re-entered.
- **Interrupts valid anywhere** (robot question, scam question, unknown fact): short rules in `system_prompt`, or a global node with `excluded_nodes`.

## 5. Format rules that bite

- Nodes: `tools` only on `conversation` nodes, `pre_actions` only on `api_request` and `code` nodes (the platform drops the rest silently). Passthrough nodes end with an `always` transition. Use snake_case keys, omit `agent_config`, no `null`. `max_node_turns` defaults to 10 user turns: set a realistic cap on every conversation node together with a `max_turn_transition` to a safe close. `context_variables` are dropped on save: do not use them.
- Transitions: first match wins, specific before broad. A top-level condition group is always `"logic": "or"`; nest an `and` group inside it. Do not route on a boolean.
- Prompts: `task_message` covers this node's job, names its tools and says when to call them, never names other nodes. Tool descriptions are instructions with the trigger ("CALL it every time ..."). One tool per message. After every tool result the agent must speak: give it `what_to_do_next`, or it says nothing or ignores a negative result.
- Tools: fixed values are `default`, never `const`. Each body field is a leaf under `body.properties` with its own `default`, `description`, `enum`. A `{{var}}` default that has no value makes the model fill the field; an unset single placeholder drops the field from the request. Give model-filled values an `enum`. Model arguments are stored as `<tool>_args.<field>`.
- Code: reads and writes through `vars`, never raises, no `{{` or `}}`, only `json`, `re`, `datetime`. A code node returns no data; its values are `vars`.
- Extraction (use it sparingly, only for customer speech): set `min_confidence` on every variable (the default 0.95 silently discards), type dates as `date`. Use `response_mapping` for bank answers.

## 6. Finish

Write `workflow.json`. Run `python3 tools/lint.py workflow.json`, then `python3 tools/publish.py workflow.json`. Fix until both are clean, including any `READBACK` line (the platform silently dropped something). Then continue with the test-and-repair skill, which runs the practice customers against the published agent.
