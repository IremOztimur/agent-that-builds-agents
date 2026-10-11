# Report

Final version: v4 (`workflow.json` = `versions/v4.json`), published. practice.py said STOP after four rounds.

| Version | Round | Passed | Failed |
|---|---|---|---|
| v1 | r1 | 8 / 13 | PUB-07, 08, 09, 10, 13 |
| v2 | r2 | 9 / 13 | PUB-07, 10, 12, 13 |
| v3 | r3 | 10 / 13 | PUB-01, 04, 13 |
| v4 | r4 | 11 / 13 | PUB-04, 06 |

## Causes repaired
See `repairs.md`: transfer reason lost (STATE), already-paid closed as refused (RULE_MISSED), no retry after one failed create_promise (NOT_ENFORCED), named date counted as a refusal (NLU -> code), premature `done` / goodbye loop (STATE, STALL), `done` on an agreement to pay (NOT_ENFORCED).

## What still fails
- PUB-04 (conversation only; ledger correct): the model still calls `report refusal` when the customer names her own date. The code ignores it (no attempt is used), but the judge sees the call. Failed in r3 and r4.
- PUB-06 (conversation only; ledger correct): new in r4, passed in r1-r3. Transcript not inspected (no time); not rerun alone, so it may be noise.
- PUB-13 passed in r4 but failed r1-r3; joint read-back for several products is prompt-driven and unstable.
- No failure was rerun with `--only`, and the r4 failures were not read: the clock ran out.

## Unverified
- Brief A vs B is chosen by product count (1 -> no add_note). No practice case contradicted it.
- Workflow is 1,055 lines, above the 600-line target (lint warning only).
