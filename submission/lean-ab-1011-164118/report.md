# Report

Published: workflow.json = versions/v1.json, agent bae2883b-c8b6-4e8d-a539-1780a3ee287c.

| Version | Round | Score |
|---|---|---|
| v1 | r1 | 7 / 13 |

One round only. It took 433 s and left about 5 minutes, below the stop threshold, so no repair round was run and failures were not rerun with --only.

The derived expectations matched the known ones for 13 of 13 customers (product ids are p1, p2, p3).

Passed: PUB-01, 02, 03, 05, 08, 09, 11.

Still failing:
- Wrong bank record: PUB-04, PUB-07, PUB-13.
- Bank record correct, conversation check failed: PUB-06, PUB-10, PUB-12.

Causes (details in repairs.md):
- PUB-04: a date said in words was not parsed, and the code then treated the reply as a refusal. Confirmed in the transcript. This is the most important fix and is general: any customer who says a date in words is affected.
- PUB-13: probably the same, plus notes followed by a transfer. Only partly read.
- PUB-06: the floor offer was repeated after a clarifying question. Confirmed in the transcript.
- PUB-07, PUB-10, PUB-12: not diagnosed; transcripts not read.

Platform assumptions from Phase 1 that the round confirmed: hooks read variables written by the code node, the code-node round trip produces the next line, the end-of-call close works, the callback and three-wrong-answers paths close correctly.
