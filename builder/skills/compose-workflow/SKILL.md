---
name: compose-workflow
description: Design and write the Freya phone-agent workflow (workflow.json) from rules.json, enforcing every hard rule by structure or code and mapping each rule to a mechanism in design.md.
---

# Compose the workflow

Read first: `docs/workflow-format.md`, `docs/tools-and-code.md` (the format; follow them exactly) and `examples/base-agent.json` (the shape of a working agent). Read no other workflow. Every value (dates, limits, outcome names, queue names, phrases) comes from `rules.json` or `tools.json`, never from memory.

## 1. design.md first

One row per live rule (decided, proposed, or unresolved-with-the-stricter-reading): `rule id | mechanism | where`.
Mechanisms: `structure` (a tool is absent from every node where it must not be callable; node order; a transition on the bank's own answer), `code` (a code node or hook computes, validates or counts), `prompt` (wording only).
Rules of class gate, calc and state may not use `prompt`. If you cannot enforce one, write it under "not enforced" with the reason: do not hide it in prompt text.

## 2. Shape

The smallest workflow that works: at most about 600 lines pretty-printed, usually 4 to 8 nodes. Typical stages: who is on the line, identity, one code node for facts, the conversation node that holds the tools, one closing path. Do not make a node per rule.

## 3. Patterns that work on this platform

- **Gate by structure.** List a protected tool only in a node reachable through a transition whose condition reads a variable set from the bank's own answer (`response_mapping` or `<tool>_response.data.<field>`; test both "true" and "True"). Never gate on what the customer said, a model-extracted variable, or `matches_intent`.
- **Facts in code.** After the data call, one passthrough `code` node computes everything the prompts need (dates from `now`, deadlines, allowed-day tables, limits, finished amounts as text) into `vars`; prompts print `{{var}}`. The model never calculates dates or limits.
- **Write guard.** Every tool that writes gets a `pre_process_code` hook that checks the request against the computed limits and blocks an invalid one by setting `config['url'] = ''`. A `post_process_code` hook writes a state string to `vars` (recorded, failed, blocked) and adds a `what_to_do_next` line to `result['data']` that says what to tell the customer.
- **Counters in code.** Attempts, "only once" offers and per-item progress live in `vars` (hooks or code nodes) and are read by transitions or injected into the prompt. A prompt alone does not count reliably.
- **Closing.** The last call must match what was recorded: decide outcome and reason in the closing tool's pre hook from `vars`, not from the model's choice. Exactly one closing call, last.
- **Fixed sentences.** The opening and required sentences are `on_enter` tts text.
- **Interrupts valid anywhere** (robot question, scam question, unknown fact): short rules in `system_prompt`, or a global node.

## 4. Platform rules that bite

Tool descriptions say WHEN to call ("CALL it every time ..."). After every tool result the agent must speak: give it a `what_to_do_next`. One tool per message. No `null`. Booleans arrive as strings. Mapping paths start with `data.`. Use `default`, never `const`. Every passthrough node ends with an `always` transition. Code never raises, reads from `vars`, has no double braces. `tools` only on conversation nodes, `pre_actions` only on api_request/code nodes (the platform drops the rest silently). Keep `system_prompt` short; node prompts cover only their job.

## 5. Finish

Write `workflow.json`. Run `python3 tools/lint.py workflow.json tools.json`, then `python3 tools/publish.py workflow.json`. Fix until both are clean, including any `READBACK` line (the platform silently dropped something). Then continue with the test-and-repair skill, which runs the practice customers against the published agent.
