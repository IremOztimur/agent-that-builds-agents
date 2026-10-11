# Repairs

## Round 1 (v1: 11/13)
- PUB-03 | STATE | A14, A46-not_verified | The closing code read the wrong-answer count from the flattened tool-result variable, which is not visible to code nodes, so three wrong answers closed as `declined` with the plain farewell. | verify_identity post hook now writes `id_left`; decide reads it, scans for any `*wrong_answers_left` key, and closes `declined` only when the refusal slot says twice.
- PUB-05 | NLU + NOT_ENFORCED | A32c, A41, A33 | A discount request after a job loss was extracted as a restructuring request and transferred. Hardship must come before rule 41. | The restructuring transition now requires that no hardship was mentioned; decide ignores restructuring when hardship is present; the slot description says a discount or waiver request is not restructuring.

## Round 2 (v2, talkative customers: 5/13)
- PUB-03, 10, 11, 12 | NLU | A15a, A15b | The refusal-count slot counted small talk and unfinished sentences as refusals, so the identity check closed as `declined` after two rambling replies. | Slot description now counts only explicit refusals or "what is this about" questions; identity turn cap raised to 15.
- PUB-06, 07, 13 | STALL | A30, A31 | Talkative customers gave unfinished replies until the negotiation turn cap closed the call as refused. | System prompt: no reaction to small talk, repeat the last question briefly. The cap itself stays (15 is the maximum allowed).
- PUB-05 | JUDGE_NOISE / SPEECH_CONTENT | A32a | Outcome now correct after the round 1 repair; the judge counted sympathy for small talk as a second sympathy sentence. | Covered by the small-talk rule above.
