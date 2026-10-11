# Report: Brief A

Agent `b80e092e-6d2b-4084-8be0-13dfbcf9fce2`, workflow `92938476-35ee-4f6b-9c5d-476fe9fcecf5`. `workflow.json` = `versions/v2.json`, published.

## Score per version

| Version | Run | Passed | Failed |
|---|---|---|---|
| v1 | r1 (all 10) | 9 / 10 | PUB-10: no retry after a service error on `create_promise` |
| v2 | r2 (all 10) | 9 / 10 | PUB-10: ledger correct, judge objected to the word "recorded" in the opening |
| v2 | r2b (PUB-10 only) | 1 / 1 | none |

Every practice customer has passed on v2 at least once; there was no single run with 10 / 10.

## Causes

- R37 retry was not enforced in v1 (one repair round, code + prompt). Fixed in v2.
- The remaining r2 failure is judge variance on the opening sentence the brief requires.

## What still fails or is unproven

- PUB-10 can fail again on the judge for the same wording reason; the opening cannot change without breaking brief rule 1.
- Not exercised by any practice customer, so unconfirmed: the pre hooks that block an invalid promise date/amount or an out-of-window callback (they block by raising, which the docs do not describe), the second-failure path of `create_promise`, and the `finish` refusal after one try (the model retried on its own in r2 and r2b).
- Ask-once / twice counters (second name ask, declines, floor offered once, persuasion attempts, human request) are prompt-only; see `design.md` "Not enforced".
- Ten open questions in `rules.json` were built on the stricter reading and not confirmed with the brief's owner.
- Workflow is 730 lines against a target of about 600.
- One repair round was used of the two allowed; stopped with about 8 minutes on the clock.
