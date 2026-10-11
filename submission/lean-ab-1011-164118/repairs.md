# Repairs

Round r1 (v1): 7 / 13. No repair was applied: the round ended with about 5 minutes on the clock, too little to rerun a round (one round takes about 7 minutes), so nothing could be kept under the "rerun everything" rule.

| Customer | Tag | Rule | Cause | Change (proposed, not applied) |
|---|---|---|---|---|
| PUB-04 | NLU | A23-after, A29-notrefusal | Transcript read. The customer said the date in words ("the sixth of November"). The date slot did not give the code a parseable day, so the code saw no date and treated the reply as a flat refusal, used both attempts and closed refused. | Ask the `date_said` slot for "day as a number plus month name"; in `brain` step(), a `proposes` reply with no parsed day or amount asks for the exact day instead of using a persuasion attempt; parse day words in code. |
| PUB-13 | NLU (probable) | B6-one-date | Transcript only partly read. Both products were noted refused and the call went to the support queue; likely the same unparsed date, plus a reply read as hardship/accept support. Notes were written before a transfer, which B10 forbids. | Same date fix; block `transfer_to_agent` in the pre hook once any note exists, and block notes once hardship support was offered. |
| PUB-07 | not diagnosed | A21-vague, A20-holiday | Transcript not read. Closed as not_reached / unclear after get_account, which only happens when the code node fell into its error branch. | Read the transcript; make the error fallback keep the last valid stage instead of the default outcome. |
| PUB-06 | SPEECH_ORDER | A26-floor-once | Transcript read. Bank record correct. After a clarifying question the agent repeated the whole floor offer, which the judge counted as offering the floor twice. | For a `question` reply, the step should say "answer only, do not restate the offer". |
| PUB-10 | not diagnosed | A37-ok | Bank record correct (retry worked, promise recorded). Conversation check failed; transcript not read. | Read the transcript first. |
| PUB-12 | not diagnosed | B5-attempts | Bank record correct (one promise, two refused notes). Conversation check failed; transcript not read. | Read the transcript first. |
