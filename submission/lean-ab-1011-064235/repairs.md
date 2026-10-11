# Repairs

## Round 1 -> v2 (8/13 -> 9/13)
- STATE, A41/B10 (PUB-09): transfer reason fell back to `human` because the post hook could not read the model's `queue` argument. Change: transfer_to_agent pre hook stores the queue in vars; post hook and close hook read it.
- RULE_MISSED, A39 (PUB-08): model said the one-business-day sentence itself and closed with `done` -> no_promise/refused. Change: prompt tells it to call report already_paid / dispute at once (code closes as paid / dispute).
- NOT_ENFORCED, A37 (PUB-10): model reported service_error after one failed create_promise. Change: report code closes on service_error only after two failures; otherwise tells it to retry.
- NLU, A20/A29 (PUB-07): a named holiday date was reported as a refusal. Change: prompt rule (not enough, see round 2).
- STATE, B6/B7 (PUB-13): `done` reported before the second create_promise; product on a later date than its deadline. Change: report code ignores `done` while a product has neither promise nor note; facts text gives the per-product deadline rule.

## Round 2 -> v3 (9/13 -> 10/13)
- NLU -> code, A29 (PUB-07): report gets a required argument named_date_or_amount; code does not count a refusal when it is yes.
- STALL, A46 (PUB-13): call looped on goodbyes because `done` was never reported again. Change: create_promise post hook and add_note pre hook close the call themselves once every product has a promise or a note; the bye line carries the text-message sentence.
- PLATFORM (PUB-12): close_call went out empty once; same tool sequence passed in r1 and r3. No change.
- JUDGE_NOISE (PUB-10): judge objected to "this call is recorded" in the opening, which the brief requires. No change.

## Round 3 -> v4
- NOT_ENFORCED, A34 (PUB-01): model reported `done` when the customer agreed to pay today; code closed as no_promise/refused. Change: with one product, `done` with nothing recorded does not close the first time; code tells the model to read back and record.
- NLU / JUDGE (PUB-04): the model called report refusal with named_date_or_amount=yes; the code ignored it (no attempt counted) but the judge saw the call. Change: prompt line only.
- SPEECH, B7 (PUB-13): products were confirmed one at a time instead of one joint read-back. Not repaired (no time).
