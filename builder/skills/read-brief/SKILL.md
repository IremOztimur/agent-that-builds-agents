---
name: read-brief
description: Phase 0. Read the brief (any form, any file name) into a checked rules.json, then derive what each practice topic must leave in the bank.
---

# Phase 0: read the brief

`cat inputs.json` names the brief and the tool API, both under `input/`. The brief can have any name and any form: specification, mail, memo, notes, transcript. These two files and `docs/` are the only truth; use nothing from memory.

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
6. `topics.json` lists the practice customers: what each one does, not what the bank must show. Each product has the id the bank uses (`p1`, `p2`, ...); use it as `product_id`. For each, work out from `rules.json` alone what the call must leave in the bank and say, and write `expectations.json`: `{"<topic id>": {"outcome", "reason", "promises": [{"product_id", "amount", "date"}], "notes", "callbacks", "transfers", "must_state", "must_not", "rules": [ids]}}`. Dates and amounts come from the brief's calendar and tables applied to that customer's products and `now`. If a rule does not settle an expectation, the rule is missing or wrong: fix `rules.json`, not the guess.
7. `python3 tools/check_expectations.py`.

Done when `check_rules` and `check_expectations` say ok.
