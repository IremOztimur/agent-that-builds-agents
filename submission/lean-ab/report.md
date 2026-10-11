# Report

Published version: v4 (`workflow.json`, agent 1d7de975-951a-4e1d-9fd7-ea9d3e4d7321).

| Version | Run | Passed | Failed |
|---|---|---|---|
| v1 | r1, all 13 | 8 | PUB-07, 09, 10, 11, 13 |
| v2 | r2, all 13 | 11 | PUB-12, 13 |
| v3 | r3, all 13 | 11 | PUB-10, 12 |
| v4 | r4, 5 customers only | 3 of 5 | PUB-10, 12 |

v4 was NOT run on all 13 customers: the clock ran out. It was run on PUB-01, 10, 11, 12, 13. The other eight passed in r2 and r3 and the v4 changes do not touch their paths, but that is not measured. Failures were not rerun once with `--only` as the skill asks, so model variance is not separated from real faults.

## Causes found
- Shared state overwritten by parallel create_promise calls (fixed, PUB-11 and PUB-13 pass).
- Agent stalls when it speaks before calling the report tool (fixed, PUB-09 passes).
- Holiday before the deadline answered with the deadline (fixed in code, PUB-07 passes).
- Post hook does not seem to run when the bank returns a service failure, so failure handling cannot rely on it. v4 uses the engine's success counter and one engine retry instead.

## What still fails
- PUB-12 (three products): the agent makes two persuasion attempts on a product that allows one. The count is kept in code, but nothing stops the agent from speaking a second offer; this is still prompt-level.
- PUB-10 (create_promise fails once): the ledger is now right, the judge still fails the conversation. The v4 transcript was not read.

## Not confirmed
- Whether the engine retry or the model made the second create_promise call in r4.
- Three once-only counts remain prompt-level: asking once for an exact day, offering the floor once, asking once before a human transfer.
- The workflow is 1026 lines against a target of about 600.
- The Brief A/B add_note question: notes are written only for two or three products; all practice customers that passed are consistent with this.
