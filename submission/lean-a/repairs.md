# Repairs

## Round 1 (v1 -> v2)

| Tag | Rule | Cause | Change |
|---|---|---|---|
| NOT_ENFORCED | R37.retry | `create_promise` returned a service error; the agent did not try once more and closed `no_promise` / `service_error` after a single try. The post hook's retry instruction did not take effect on a failed call. | Code: the `create_promise` pre hook counts tries (`promise_tries`); the `finish` code refuses to close `service_error` after exactly one try and tells the model to call `create_promise` again. Prompt: step 5 states the retry explicitly and says to say only that the promise could not be recorded. |
| SPEECH | R44.unknown | After the failure the agent told the customer to "call our customer service team", which is not in the brief. | Same prompt line: "say only that you could not record the promise". |

Result: r2 recorded the promise on the second try with outcome `promise`. Nothing that passed in r1 failed in r2. Kept.

## Not repaired

| Tag | Rule | Cause |
|---|---|---|
| JUDGE_NOISE | R1.opening | r2 PUB-10: the judge counted the opening's "this call is recorded" (required by brief rule 1) as saying "recorded" before the promise was stored. Rerun r2b of the same customer on the same version passed. No change made. |
