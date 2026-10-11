---
name: test-and-repair
description: Phase 2. Run the practice customers and repair in rounds, as long as there is time and the failures keep going down.
---

# Phase 2: test and repair

`tools/practice.py` plays the practice customers (`cases` in `inputs.json`: A, B or AB) against your published agent. You see what happened, never what was expected: get the requirement from the brief.

Repeat rounds while there is time, but `practice.py` decides when to stop: it prints STOP and refuses another full round when everything passes, when you are already strong and the last repair changed nothing, when the same failures survive two repairs, or after four rounds. Also stop when `python3 tools/clock.py` shows under 5 minutes. A failure that survives a repair is usually the judge or a customer's wording, not a rule of the brief: do not chase it with a customer-specific fix.

1. `python3 tools/practice.py run <agent_id> --brief <cases> --name rN` (it has its own time limit and heals platform blocks; do not wrap it in `timeout`). Save the workflow as `versions/vN.json` and the result in `scores.json`.
2. Run failures once more with `--only`: the customers and the judge are models and vary.
3. `python3 tools/practice.py show rN`: which part was wrong, the judge's reason, the transcript with tool calls.
4. Group failures by cause and tag them: RULE_MISSED, RULE_WRONG, NOT_ENFORCED, STATE, SPEECH, NLU, STALL, PLATFORM, JUDGE_NOISE. Write tag, rule id, one-line cause and the change to `repairs.md`.
5. Fix at the layer the tag names, as a rule about calls that holds for every customer, product, amount and date. Never put a customer's id, name, amount or date in the workflow. NOT_ENFORCED means structure or code, not more prompt text. Keep `design.json` true.
6. Publish and rerun everything. Keep the change only if the failures went down and nothing that passed now fails. Otherwise restore the previous version and try a different fix for the same cause.
7. Next round, unless `practice.py` said STOP.

Finish with the best version in `workflow.json`, published, and `report.md`: score per version, causes, what still fails.
`python3 tools/run_code.py` runs one code snippet locally if you need to check a calculation.
