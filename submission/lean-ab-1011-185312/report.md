# Report

| Version | Round | Passed |
|---|---|---|
| v1 | r1 | 10 / 13 |
| v2 (published, workflow.json) | r2 | 13 / 13 |

Expectations matched the oracle for 13 of 13 customers.

## Causes repaired in v2
- A26/A30: after "too much", one floor offer (today or by the last business day of the week), the full amount is never offered again.
- A37: a failed create_promise is retried at once, without speaking or re-confirming.
- A18/B5: an early-band product gets exactly one persuasion offer.

## What still fails (talkative style only, v2, not counted)
- Small talk during the security questions is taken as a second refusal: the call closes as not_verified / declined. The fix (an explicit tool-call transition instead of the id_stance slot) was written but never applied or tested; time ran out.
- A customer who keeps not answering gets the same offer repeated; a non-answer is not counted as a refusal, and one call did not close in time.
- When a call ends without reaching the settle step, close_call falls back to not_reached / unclear even after verification.
