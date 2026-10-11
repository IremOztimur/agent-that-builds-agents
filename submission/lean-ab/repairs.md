# Repairs

## Round 1 (v1, 8/13)
- STATE, B7/B8a (PUB-11, PUB-13): parallel create_promise calls overwrote one shared state variable, so a promised product got a `refused` note. Change: per-product variables written by the hooks.
- STALL, A30a (PUB-09): the agent spoke, then called `mark`, then had nothing to say; the call died before the restructuring request. Change: prompt says call the tool first, speak after; "cannot pay that amount" is the floor offer, not an attempt.
- NOT_ENFORCED, A20 (PUB-07): a holiday before the deadline was answered with the deadline. Change: facts code lists every non-business day before the deadline with the day to offer instead.
- SPEECH, A37 (PUB-10): after the first failed create_promise the agent told the customer and asked again. Change: prompt says retry silently and never say "recorded" before success.

## Round 2 (v2, 11/13)
- STATE, B7 (PUB-13): the per-product flags still raced (both hooks credited the same product). Change: a product counts as promised when its request was sent and not known to have failed.
- NLU (PUB-13): the agent called a Friday a Saturday. Change: prompt says read weekdays from the calendar only.
- NOT_ENFORCED, B4b/B5 (PUB-12): two attempts on an early-band product. Change: prompt says the first per-product proposal is attempt 1. Still prompt-level.

## Round 3 (v3, 11/13)
- RULE_WRONG, A37/A46 (PUB-10): the round-2 change counted a failed, never-retried promise as recorded and closed as `promise` with nothing in the ledger. The post hook does not appear to run on a service failure. Change: promised status now uses the engine's success counter; a sent but unrecorded product is `service_error`; create_promise gets one engine retry.
- NOT_ENFORCED, B5 (PUB-12): unchanged cause; facts text for one-attempt products made stricter.

## Round 4 (v4, partial run)
- PUB-10: ledger now correct (two calls, promise recorded); the judge still fails the conversation. Not investigated (out of time).
- PUB-12: still two attempts on the early-band product.
