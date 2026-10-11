---
name: test-and-repair
description: Phase 2. Run the practice customers and repair in rounds, as long as there is time and the failures keep going down.
---

# Phase 2: test and repair

`tools/practice.py` plays the practice customers (`cases` in `inputs.json`: A, B or AB) against your published agent. Each customer is a topic: a kind of call (see `topics.json`). A hidden customer raises the same topic in other words, with other amounts and dates. What counts is your `expectations.json`, derived from `rules.json`; you never see another set of expected values. A repair must be a rule about calls, not about one customer.

Repeat rounds while there is time, but `practice.py` decides when to stop: it prints STOP and refuses another full round when everything passes, when you are already strong and the last repair changed nothing, when the same failures survive two repairs, or after four rounds. Also stop when `python3 tools/clock.py` shows under 5 minutes. A failure that survives a repair is usually the judge or a customer's wording: do not chase it with a customer-specific fix.

1. `python3 tools/practice.py run <agent_id> --brief <cases> --name rN` (it has its own time limit and heals platform blocks; do not wrap it in `timeout`). Save the workflow as `versions/vN.json` and the result in `scores.json`.
2. Run failures once more with `--only`: the customers and the judge are models and vary.
3. `python3 tools/practice.py show rN`: which part was wrong, the judge's reason, the transcript with tool calls.
4. Tag each failure by cause: RULE_MISSED, RULE_WRONG (rules.json), ORACLE (the expectation was wrong: fix it in `expectations.json` from the brief, not from the result), NOT_ENFORCED, STATE, SPEECH_CONTENT (a required fact or wording missing or wrong), SPEECH_ORDER (right content, wrong order or shape), VISIBLE_CALL (a tool call the model should not make or name, even though the code ignored it), NLU, STALL, API_MISMATCH (the bank rejects a field or value the tool API of this brief defines), PLATFORM, JUDGE_NOISE. Write tag, rule id, one-line cause and the change to `repairs.md`.
5. Fix at the layer the tag names, as a rule about calls that holds for every customer, product, amount and date. Never put a customer's id, name, amount or date in the workflow. NOT_ENFORCED, STATE: structure or code. SPEECH_CONTENT, SPEECH_ORDER: the policy slice of the node that owns the step, or a code-computed fact it shows. VISIBLE_CALL: intent through an extraction slot, one write by code. Keep `design.json` true.
6. Publish and rerun everything. Keep the change only if the failures went down and nothing that passed now fails. Otherwise restore the previous version and try a different fix for the same cause.
7. Next round, unless `practice.py` said STOP.
8. Once, when a full round has at most two failures or two rounds are done and at least 8 minutes are left: one round with `--style talkative` on every customer. It is reported, not counted. Hidden customers talk like people; repair only what shows a rule about calls.

Finish with the best version in `workflow.json`, published, and `report.md`: score per version, causes, what still fails.
`python3 tools/run_code.py` runs one code snippet locally if you need to check a calculation.
