# Design

6 nodes: setup (code) > identity (conversation) > load_account (api_request) > facts (code) > collection (conversation) > goodbye (end_call). Lifecycle `close_call` at end_of_call.

| id | class | mechanism | where |
|---|---|---|---|
| S1.scope | flow | code | facts: first product only |
| S1.job | flow | structure | setup>identity>load_account>facts>collection>goodbye |
| S2.vars_only | gate | structure | account facts exist only after load_account/facts |
| S2.customer_id | gate | structure | baked default {{customer_id}} in every api tool |
| S2.name | speech | prompt | identity |
| S2.title | speech | prompt | system_prompt |
| S2.now | calc | code | FACTS reads vars['now'], never the clock |
| R1.opening | speech | structure | identity.on_enter tts |
| R1.no_reason_words | gate | structure+prompt* | identity node has no account data; wording by prompt |
| R2.ask_name | speech | structure | identity.on_enter tts |
| R3.confirmation | flow | prompt | identity |
| R3.second_ask | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R3.question_first | flow | prompt | identity |
| R4.robot | speech | prompt | system_prompt |
| R5.third_party_silence | gate | structure+prompt* | identity node has no account data; wording by prompt |
| R5.ask_when | speech | prompt | identity |
| R6.callback_window | calc | code | FACTS callback_facts + schedule_callback pre hook blocks |
| R6.schedule | outcome | code | schedule_callback post hook what_to_do_next; finish coerces callback->no_callback if not booked |
| R7.outside_window | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R8.wrong_number | outcome | prompt | identity |
| R9.deceased | outcome | prompt | identity |
| R10.relative | gate | structure | get_account/create_promise not in identity node |
| R11.two_questions | flow | prompt | identity |
| R11.verify_call | gate | structure | verify_identity tool, identity node |
| R11.dob_format | calc | code | verify post hook: unreadable -> ask again |
| R11.numeric_dmy | calc | prompt (NOT ENFORCED) | identity/collection task_message |
| R12.three_wrong | state | code | bank counter wrong_answers_left read by verify post hook |
| R13.swap_hint | flow | code | verify post hook on hint |
| R14.failed | outcome | structure | no path to load_account without all_verified; post hook names finish |
| R15.decline | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R15.what_about | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R16.get_account | gate | structure | load_account pre_action, reached only via transition on all_verified |
| R17.state_debt | speech | prompt | collection |
| S7.business_days | calc | code | FACTS + create_promise pre hook holiday list |
| R18.deadline | calc | code | FACTS |
| R18.early | calc | code | FACTS |
| R18.late | calc | code | FACTS |
| R19.valid_date | gate | code | create_promise pre hook blocks |
| R20.non_business | flow | code | FACTS calendar row names the next business day |
| R21.vague | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R22.weekday_words | calc | code | FACTS calendar labels this week / next week |
| R23.after_deadline | flow | code | FACTS calendar row + pre hook |
| R24.full_first | speech | prompt | collection |
| R24.never_how_much | gate | prompt* | collection |
| R25.floor | calc | code | FACTS |
| R26.too_much | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R26.floor_refused | flow | prompt | collection |
| R27.accept_range | calc | code | create_promise pre hook blocks outside floor..full |
| R27.below_floor | state | code | pre hook blocks; once-offer by prompt (see not enforced) |
| R28.first_ask | speech | prompt | collection |
| R29.proposal_not_refusal | flow | prompt | collection |
| R30.flat_refusal | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R30.attempt1_amount | calc | code | FACTS text |
| R30.attempt1_date | calc | code | FACTS |
| R30.attempt2 | calc | code | FACTS: absent for early band |
| R31.stop | outcome | prompt | collection |
| R32.hardship | flow | prompt | collection |
| R32.support_accept | outcome | prompt | collection |
| R32.support_decline | outcome | prompt | collection |
| R32.precedence | flow | prompt | collection |
| R33.no_extra_terms | gate | prompt* | system_prompt |
| R34.read_back | gate | code | pre hook validates; yes-gate by tool description (see not enforced) |
| R35.change | flow | prompt | collection |
| R36.one_promise | state | code | promise_ok flag; pre hook blocks a second create_promise |
| R37.recorded_only_ok | gate | code | create_promise post hook; finish coerces promise without promise_ok |
| R37.retry | state | code | promise_fail counter in post hook; maxRetries 0 |
| R38.sms_sentence | speech | code | post hook what_to_do_next carries the sentence |
| R39.already_paid | outcome | prompt | collection |
| R40.dispute | outcome | prompt | collection |
| R40.closed_is_dispute | flow | prompt | collection |
| R41.restructuring | outcome | prompt | collection |
| R42.human | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R43.scam | speech | prompt | system_prompt |
| R44.unknown | gate | prompt* | system_prompt |
| R45.no_talk | state | prompt (NOT ENFORCED) | identity/collection task_message |
| R45.human_anytime | flow | prompt | collection |
| R46.close_once | gate | structure | lifecycle end_of_call close_call, outcome/reason from vars set by finish code |
| T.promise | outcome | code | FINISH |
| T.paid | outcome | code | FINISH |
| T.transferred | outcome | code | FINISH + transfer_ok |
| T.no_promise | outcome | code | FINISH |
| T.not_verified | outcome | code | FINISH: unverified stage cannot close promise/paid/no_promise |
| T.not_reached | outcome | code | FINISH |
| S12.transfer_after_promise | outcome | code | FINISH keeps transferred over promise |
| S12.no_add_note | gate | structure | add_note tool does not exist in the workflow |
| R47.goodbye | speech | structure | goodbye end_call spoken_message |

## Not enforced (prompt only)

- R3.second_ask, R7.outside_window, R15.decline, R15.what_about, R21.vague, R26.too_much, R30.flat_refusal, R42.human, R45.no_talk (state): ask-once / twice counters are counted by the model from the prompt. A code_exec report tool per counter was not built: 18 minutes on the builder clock.
- R11.numeric_dmy (calc): the model converts the spoken date; the bank's day_month_swapped hint is the only check.
- R34.read_back (gate): the clear yes before create_promise is a model judgement; the hook only checks date, amount, product and once-only.
- prompt* gates (R1, R5, R24, R33, R44): spoken-word prohibitions; no mechanism can filter speech. Structure only guarantees the account data is absent before verification.
- Pre hooks block by raising; what the platform does with a raising hook is undocumented (docs/tools-and-code.md). To be confirmed in phase 2.
- Workflow is 730 lines (target about 600): hook code and prompts.
