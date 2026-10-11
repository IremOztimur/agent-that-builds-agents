---
name: read-brief
description: Phase 0. Read the brief (any form, any file name) into a checked rules.json.
---

# Phase 0: read the brief

`cat inputs.json` names the brief and the tool API, both under `input/`. The brief can have any name and any form: specification, mail, memo, notes, transcript. These two files and `docs/` are the only truth; use nothing from memory.

1. Read the tool API completely: operations, fields, allowed values, which operations write.
2. Read the brief completely and in order, 150 lines at a time, to its last line. Searching for keywords is not reading.
3. Write `rules.json`: `{"brief_lines": N, "rules": [], "unused": {}, "skipped_lines": {}, "open_questions": []}`. One rule per atomic obligation, prohibition, permission, definition or table row, with:
   - `id`, `quote` (verbatim from the brief), `stage`, optional `note` and `refs`
   - `class`: gate (must never happen unless a condition holds), calc (a derived value), state (counters, once-only, per item), speech, flow (reaction to the customer), outcome (how the call closes)
   - `status`: decided, proposed, rejected, example, superseded, unresolved
4. Mails, memos, notes: a hedge or a question is `proposed`. A later explicit amendment marks the earlier rule `superseded` (`refs`). Conflicts nothing resolves are `unresolved`: build the stricter reading and list it in `open_questions`.
5. Run `python3 tools/check_rules.py`. Fix every FAIL. Answer every WARN with a rule, or an `unused` / `skipped_lines` entry with a reason.

Done when `check_rules` says ok.
