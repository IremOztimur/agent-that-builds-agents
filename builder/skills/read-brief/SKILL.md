---
name: read-brief
description: Phase 0. Read the brief (any form, any file name) into a checked rules.json, then derive what each practice topic must leave in the bank.
---

# Phase 0: read the brief

`cat inputs.json` names the brief and the tool API, both under `input/`. The brief can have any name and any form: specification, mail, memo, notes, transcript. These two files and `docs/` are the only truth; use nothing from memory.

If `inputs.json` says `"mode": "final"`, the input is a case folder of documents (any language, Turkish for the final): `input/corpus.md` holds the text of every document in reading order (BRIEF.md first, README.md says what each is), the originals are in `input/original/`, `tools` is the machine-readable service contract if there is one (otherwise it is one of the documents), and `base_url` is the mock the tools call: every tool URL is `base_url` plus the contract's path. Documents listed under `unconverted` (drawings, images, PDFs with no text) are read with the Read tool; a rule taken from one has `source` (the file name) and a `note` instead of a verbatim quote. A later announcement or Q&A answer that changes a rule supersedes it (`refs`). Write every customer-facing sentence, and every `wording` rule, in the language of the documents.

1. Read the tool API completely: operations, fields, allowed values, which operations write.
2. Read the brief completely and in order, 150 lines at a time, to its last line. Searching for keywords is not reading.
3. Write `rules.json`: `{"brief_lines": N, "rules": [], "unused": {}, "skipped_lines": {}, "open_questions": []}`. One rule per atomic obligation, prohibition, permission, definition or table row, with:
   - `id`, `quote` (verbatim from the brief), `stage`, optional `note` and `refs`
   - `class`: gate (must never happen unless a condition holds), calc (a derived value), state (counters, once-only, per item), speech, flow (reaction to the customer), outcome (how the call closes)
   - `status`: decided, proposed, rejected, example, superseded, unresolved
   - `kind`, how the rule will be enforced: gate (order, a condition before an action), limit (a number, count or derived value), allowed_set (what may or may not be offered or done), wording (exact words the brief mandates: add `wording`, verbatim), content (facts that must be conveyed), style (tone, manner)
   - `applies`: the situation in which it is in force, in plain words; `depends_on`: ids of rules it overrides or limits
4. Mails, memos, notes: a hedge or a question is `proposed`. A later explicit amendment marks the earlier rule `superseded` (`refs`). Conflicts nothing resolves are `unresolved`: build the stricter reading and list it in `open_questions`.
5. Run `python3 tools/check_rules.py`. Fix every FAIL. Answer every WARN with a rule, or an `unused` / `skipped_lines` entry with a reason.
6. Dev mode: `topics.json` lists the practice customers: what each one does, not what the bank must show. Final mode: write `topics.json` yourself from the bank's test customers and example conversations: a list of `{"id", "title", "script", "variables", "ledger_id"}`, one per kind of call (identity, payment, dispute, refusal, a relative answering, a tool failing, several accounts: whatever the documents show), `script` = who the customer is and what they do on the call, in the documents' language, with the facts the call needs (including wrong answers where the call has them); `variables` = what the call starts with (the customer id the mock knows, and anything the workflow reads); `ledger_id` = the id the mock files that customer's calls under. Every kind of call in the example conversations is a topic. Each product has the id the bank uses (`p1`, `p2`, ...); use it as `product_id`. For each, work out from `rules.json` alone what the call must leave in the bank and say, and write `expectations.json`: `{"<topic id>": {...}}`. Practice bank: `outcome`, `reason`, `promises` [{product_id, amount, date}], `notes`, `callbacks`, `transfers`. A mock: `calls` [{"tool", "args": {only the arguments that matter}}], `forbidden_calls` [tool names], `state` {...}. Both: `must_state`, `must_not`, `rules` [ids]. Dates and amounts come from the brief's calendar and tables applied to that customer's products and `now`. If a rule does not settle an expectation, the rule is missing or wrong: fix `rules.json`, not the guess.
7. `python3 tools/check_expectations.py`.

Done when `check_rules` and `check_expectations` say ok.
