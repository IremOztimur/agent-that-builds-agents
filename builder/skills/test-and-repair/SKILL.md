---
name: test-and-repair
description: Phase 2. Run the practice customers, find the causes, repair in bounded rounds.
---

# Phase 2: test and repair

`tools/practice.py` plays the practice customers (letter `cases` in `inputs.json`) against your published agent. You see what happened, never what was expected: get the requirement from the brief.

At most two repair rounds, one run each. Stop when everything passes or `python3 tools/clock.py` shows under 6 minutes.

1. `python3 tools/practice.py run <agent_id> --brief <letter> --name rN` (it has its own time limit and heals platform blocks; do not wrap it in `timeout`). Save the workflow as `versions/vN.json` and the result in `scores.json`.
2. Run failures once more with `--only`: the customers and the judge are models and vary.
3. `python3 tools/practice.py show rN`: which part was wrong, the judge's reason, the transcript with tool calls.
4. Group failures by cause and tag them: RULE_MISSED, RULE_WRONG, NOT_ENFORCED, STATE, SPEECH, NLU, STALL, PLATFORM, JUDGE_NOISE. Write tag, rule id, one-line cause and the change to `repairs.md`.
5. Fix at the layer the tag names, as a rule about calls that holds for every customer. Never put a customer's id, name, amount or date in the workflow. NOT_ENFORCED means structure or code, not more prompt text.
6. Publish and rerun everything. Keep the change only if the target is fixed and nothing that passed now fails; otherwise restore the previous version.

Finish with the best version in `workflow.json`, published, and `report.md`: score per version, causes, what still fails.
`python3 tools/run_code.py` runs one code snippet locally if you need to check a calculation.
