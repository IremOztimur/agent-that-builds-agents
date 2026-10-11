---
name: test-and-repair
description: Run the practice customers against the published agent, read the bank's ledger and the judge's verdict, tag each failure by cause, and repair the workflow in bounded rounds without regressions. Use after compose-workflow.
---

# Test and repair on the practice customers

The practice customers for this brief are played against your published agent in text by `tools/practice.py`. You see what happened, never what was expected or what the customers were told to do: work out what the brief requires from the brief, then check what your agent did against that. A customer passes only if all three hold: the bank's ledger is right (outcome, promises, notes, callbacks, transfers), the conversation stayed inside the brief, and the agent told the truth. The ledger comes from the bank, never from what the agent said. There is no partial credit, and one green run is a hint, not proof.

## The loop

0. `python3 tools/clock.py` shows the minutes left. Never start a run you cannot finish: ten customers take about 3 to 6 minutes. Keep the last 5 minutes free.
1. **Publish and save.** `python3 tools/publish.py workflow.json` prints the `agent_id`. Copy the file to `versions/v1.json`.
2. **Run.** In the foreground, and wait for it to end: `python3 tools/practice.py run <agent_id> --brief <A or B> --name r1`. It prints, per customer, pass or fail, the tool calls, and for a failure which part was wrong and what your agent actually recorded. Add the result to `scores.json` (version, passed ids, failed ids). One repetition per run is enough for now: do not use `--reps`.
3. **Re-run failures once** with `--only ID,ID --name r1b`. The simulated customer and the judge are models and vary between runs. A customer that passes on the second run is noise, not a bug; note it.
4. **Read every real failure.** `python3 tools/practice.py show r1` prints, per failure, which part was wrong, the judge's reason (numbers and months masked), and the transcript with every tool call and routing step. Ask yourself: what does the brief require here, and what did the agent do instead?
5. **Tag by cause, then group.** Many failures share one cause; fix the cause once.
   - `RULE_MISSED`: the brief has a rule, the workflow has no mechanism for it
   - `RULE_WRONG`: the rule was misread; re-read its quote in `rules.json`
   - `NOT_ENFORCED`: a gate, calculation or counter rule that exists only as prompt text, and the model broke it
   - `STATE`: a counter, an order, or a "once only" is wrong or lost between steps
   - `SPEECH`: wording wrong, leaked, or a required sentence missing or said too early
   - `NLU`: the model misunderstood the customer (a date in words, a correction, a number in two parts)
   - `STALL`: no reply after a tool result, a loop, or the customer hung up after a long silence
   - `PLATFORM`: something silently dropped, a timeout, a deadlock
   - `JUDGE_NOISE`: the judge objects to something the brief itself requires or to a harmless detail
   Write each group to `repairs.md`: tag, the brief rule (id and quote), the cause in one sentence, the change and the layer it lands in.
6. **Repair at the layer the tag names.**
   - A fix is a rule about calls that holds for every customer, product, amount and date. State it that way in `repairs.md`.
   - Never put a customer id, name, amount or date from the practice set into the workflow. A failure shows that the brief was misread or enforced too weakly; it is not the specification. Re-read the brief rule, work out the correct value yourself from the rule, and implement the rule completely.
   - `NOT_ENFORCED` is fixed by moving the rule into structure or code (a gate, a code node, a hook), not by more prompt text.
7. **No regressions.** Publish the repaired workflow, save it as `versions/vN.json`, rerun all customers, update `scores.json`. Keep the change only if the targeted failures are fixed and nothing that passed before now fails. Otherwise copy the previous version back to `workflow.json`, publish it again, and note why in `repairs.md`.
8. **Stop** when everything passes in a run, after two repair rounds, or when `tools/clock.py` shows under 6 minutes.

## Finish

Copy the best-scoring version (fewest failures, latest on a tie) to `workflow.json` and publish it. Write `report.md`: the score of each version, the failure groups with their tags, what still fails and why. Print one line: the `workflow_id`, the `agent_id`, and the passed/total of the best version.

## Debug helper

`python3 tools/run_code.py workflow.json <node-or-tool name> '{"var": "value"}'` runs one code snippet of your workflow locally with the variables you give (`--hook pre|post` for a tool's hooks), so you can check a calculation without a full run.
