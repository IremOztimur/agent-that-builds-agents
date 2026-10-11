---
name: read-brief
description: Read a bank brief of any form (specification, mail, memo, meeting notes, transcript) and turn it into a checked rule list, rules.json. Use first, before designing anything.
---

# Read the brief into rules.json

Inputs in the work folder: `brief.md`, `tools.json` (the bank's tool API as OpenAPI), `docs/`. They are the only truth.
Never use rules, numbers or names you remember from any other brief.

## Steps

1. Read `tools.json` completely: every operation, field, required field and allowed value. Note which operations write bank records.
2. Read `brief.md` completely and in order, at most 150 lines at a time. Searching for keywords is not reading. Tables, footnotes, code lists and examples all count.
3. Write `rules.json` as `{"rules": [...], "unused": {}, "open_questions": []}`. One rule per atomic obligation, prohibition, permission, definition or table row; split sentences that hold several. Each rule has:
   - `id` (r01, r02, ...) and `quote`: copied verbatim from the brief
   - `class`: `gate` (must never happen unless a condition holds: protected data, writes, ordering, limits), `calc` (a value derived from inputs: dates, deadlines, amounts, bands, windows, counts), `state` (counters, "only once", per item), `speech` (required or forbidden words, disclosures), `flow` (what to do when the customer does or says X), `outcome` (how the call is closed, what is recorded)
   - `stage`: when it applies (opening, who-is-on-the-line, identity, facts, dates, amounts, persuasion, confirm, record, other-situations, closing)
   - `status`: `decided`, `proposed`, `rejected`, `example`, `superseded`, `unresolved`
   - optional `note`: your reading in plain words with the exact numbers; `refs`: ids of rules it replaces or depends on
4. Raw material (mails, memos, notes, transcripts): record who said it and where. A hedge ("maybe", "we could") or a question is `proposed`, not `decided`. A later explicit amendment ("replaces", "from now on", "instead of") marks the earlier rule `superseded` and sets `refs`. Examples and rationale are `example`. If two statements conflict and nothing resolves it, mark both `unresolved`, add it to `open_questions`, and say in the note which reading you will build: the stricter one. Never invent a rule the text does not support.
5. Run `python3 tools/check_rules.py`. Fix every FAIL. Read every WARN: each allowed value of the tool API and each number or date in the brief must be covered by a rule or listed under `unused` with a one-line reason.

## Watch for

- Every cell with a number in a table is a limit. Every row is a rule.
- Cross-references ("rule 30 applies", "see section 7"): put them in `refs`.
- The same threshold with two different numbers is a conflict, not two rules.
- Values the tool API accepts that the brief never mentions: say so in `unused`, do not guess a meaning.
