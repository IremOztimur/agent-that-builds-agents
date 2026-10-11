# Repairs

## Round 1 (v1): 10 / 13
- PUB-06 SPEECH_ORDER / NOT_ENFORCED, A26.toomuch + A30.flat: after "too much" the agent offered the floor for today, then the full amount again, then the floor on the deadline. Change: plan code states one offer 1 (full OR floor, never both) and a floor offer date; policy: floor offered once, today or by that date, with "rest stays overdue", full never offered again.
- PUB-10 SPEECH_CONTENT, A37.honest: after the first failed create_promise the agent spoke and asked for confirmation again. Change: post hook facts say retry at once with the same values, without speaking.
- PUB-12 NOT_ENFORCED, A18.early + B5.attempts: an early-band product got a second offer (the floor). Change: plan code states "exactly ONE persuasion offer in total" for early products and TWO for late.

## Round 2 (v2): 13 / 13. practice.py said STOP.

## Talkative run (not counted): 6 failures of 13 on v2
- NLU / STATE, A15.declined + A15.what: small talk or a cut-off sentence during the security questions is read as a second refusal by the id_stance extraction slot, and the call closes as not_verified / declined. Attempted change (tool-call transition instead of the slot) did NOT get applied: the edit script failed, so the published workflow is still v2. Open.
- STALL, A30.flat: with a customer who never answers, the agent repeats the same offer instead of counting a non-answer as a refusal; one call did not close in time. Open.
