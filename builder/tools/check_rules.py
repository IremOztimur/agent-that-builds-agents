"""Check rules.json against the brief and the tool API. Brief-independent.

    python3 tools/check_rules.py [rules.json] [brief file] [tool API file]     (defaults come from inputs.json)

Fails (exit 1) when a rule has no verbatim quote from the brief, or a field is missing. Warns about API enum values and
numbers or dates in the brief that no rule mentions: read each one and either add a rule or leave a one-line reason in
rules.json under "unused": {"<value>": "<reason>"}.
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import inputs

CLASSES = {"gate", "calc", "state", "speech", "flow", "outcome"}
STATUS = {"decided", "proposed", "rejected", "example", "superseded", "unresolved"}


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def enums(node, path=""):
    if isinstance(node, dict):
        if isinstance(node.get("enum"), list):
            yield path, node["enum"]
        for k, v in node.items():
            yield from enums(v, path + "/" + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from enums(v, path)


def main(rules_p="rules.json", brief_p=None, tools_p=None):
    brief_p, tools_p = brief_p or str(inputs.brief_path()), tools_p or str(inputs.tools_path())
    data = json.load(open(rules_p))
    rules = data["rules"] if isinstance(data, dict) else data
    unused = data.get("unused", {}) if isinstance(data, dict) else {}
    bad, warn, seen = [], [], set()
    raw = open(brief_p).read()
    brief = norm(raw)
    n_lines = len(raw.splitlines())
    if isinstance(data, dict) and data.get("brief_lines") != n_lines:
        bad.append("rules.json must say \"brief_lines\": %d (the number of lines you read in %s); it says %r" % (n_lines, brief_p, data.get("brief_lines") if isinstance(data, dict) else None))
    for r in rules:
        rid = r.get("id", "?")
        if rid in seen:
            bad.append("duplicate id %s" % rid)
        seen.add(rid)
        for k in ("id", "quote", "class", "status", "stage"):
            if not r.get(k):
                bad.append("%s: missing %s" % (rid, k))
        if r.get("class") not in CLASSES:
            bad.append("%s: class %r not in %s" % (rid, r.get("class"), sorted(CLASSES)))
        if r.get("status") not in STATUS:
            bad.append("%s: status %r not in %s" % (rid, r.get("status"), sorted(STATUS)))
        q = norm(str(r.get("quote", "")))
        if q and q not in brief:
            bad.append("%s: quote is not a verbatim part of the brief: %r" % (rid, r["quote"][:80]))
    text = norm(" ".join(str(r.get("quote", "")) + " " + str(r.get("note", "")) for r in rules if r.get("status") != "rejected"))
    api = json.load(open(tools_p))
    for path, vals in enums(api):
        for v in vals:
            if str(v).lower() not in text and str(v) not in unused:
                warn.append("API value %r (%s) is not mentioned by any rule" % (v, path.split("/properties/")[-1].split("/")[0]))
    for num in sorted(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b|\b\d+(?:\.\d+)?\b", brief))):
        if num not in text and num not in unused and len(num) > 1:
            warn.append("number/date %r in the brief is not covered by any rule" % num)
    quotes = [norm(str(r.get("quote", ""))) for r in rules]
    skipped = data.get("skipped_lines", {}) if isinstance(data, dict) else {}
    uncovered = []
    for i, line in enumerate(raw.splitlines(), 1):
        t = norm(re.sub(r"^[#>*\-\s|]+", "", line))
        if len(t) < 12 or any(str(a) in skipped for a in (i,)) or str(i) in skipped:
            continue
        if not any(t in q or (len(q) >= 12 and q in t) for q in quotes):
            uncovered.append("line %d: %s" % (i, line.strip()[:90]))
    for u in uncovered[:40]:
        warn.append("not covered by any rule (add a rule, or list the line under skipped_lines with a reason): " + u)
    live = [r for r in rules if r.get("status") in ("decided", "proposed", "unresolved")]
    print("rules: %d (%d live)" % (len(rules), len(live)))
    for w in warn[:60]:
        print("WARN", w)
    for b in bad:
        print("FAIL", b)
    print("check_rules:", "FAILED" if bad else "ok", "| %d warnings" % len(warn))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
