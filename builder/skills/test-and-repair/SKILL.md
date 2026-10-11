---
name: test-and-repair
description: Test the composed workflow against the rules without any bank customers (expectations written from rules.json first, local code tests, chat smoke up to the identity gate), tag every failure by cause, and repair in one bounded round.
---

# Test and repair

There are no customers for this brief. Test what can be tested without them, honestly, and report what could not be.

## 1. Expectations first

Before you read the workflow's code again, write `tests.json` from `rules.json` only: a list of
`{"rule": "r07", "name": "...", "target": "<node or tool name>", "hook": "pre|post|none", "vars": {}, "params": {}, "config": {}, "result": {}, "expect": {"vars.x": "value", "config.url": ""}}`.
For every live gate, calc and state rule write at least a passing case, a boundary case (exactly on the limit, one step beyond it) and a case that must be blocked. Work the expected values out by hand from the quote, not from what the code prints.
Run: `python3 tools/run_tests.py tests.json workflow.json`.

## 2. Conversation smoke (up to the first bank answer)

Make `vars.json` with invented call variables (customer id, names, `now` as the brief describes). The bank refuses unknown customers, so these tests cover the opening and identity stage only. Publish, then use `python3 tools/chat.py vars.json "msg" ...` for: the opening; someone else answering; the customer refusing to answer; a wrong answer; asking for the amount before identity is verified. Read the events: the protected tool must never be called, and nothing from behind the gate may be said.

## 3. Tag every failure by cause

`RULE_MISSED` (brief text with no rule or mechanism) | `RULE_WRONG` (misread: re-read the quote) | `NOT_ENFORCED` (a gate, calc or state rule that is only prompt text) | `STATE` (counter or order wrong) | `SPEECH` (wrong or leaked wording) | `NLU` (model misread the customer) | `PLATFORM` (silent drop, timeout, deadlock) | `TEST_WRONG` (expectation contradicts the quote) | `JUDGE_NOISE`.
Log each in `repairs.md`: tag, rule id, quote, the change.

## 4. Repair rules

- One round. Change the workflow at the layer the tag names, citing the quote.
- State every fix as a rule about the call, never about one scenario's words or numbers.
- Never edit `tests.json` to make a test pass. If you believe an expectation is wrong, write it to `disputed.md` with both quotes and keep the stricter behaviour.
- After the repair rerun everything: keep the change only if the target failure is fixed and nothing that passed before broke; otherwise revert it.
- Re-run lint and publish after the last change.

## 5. Report

Write `report.md`: rules enforced by structure, code, prompt only, not enforced; tests run and passed; what could not be tested (everything behind the identity gate in chat). Then print one line: `workflow.json` final, ids, tests passed/total.
