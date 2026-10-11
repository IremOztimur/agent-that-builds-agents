"""Check rules.json against the brief and the tool API. Brief-independent.

    python3 tools/check_rules.py [rules.json] [brief.md] [tools.json]

Fails (exit 1) when a rule has no verbatim quote from the brief, or a field is missing. Warns about API enum values and
numbers or dates in the brief that no rule mentions: read each one and either add a rule or leave a one-line reason in
rules.json under "unused": {"<value>": "<reason>"}.
"""
import json, re, sys

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


def main(rules_p="rules.json", brief_p="brief.md", tools_p="tools.json"):
    data = json.load(open(rules_p))
    rules = data["rules"] if isinstance(data, dict) else data
    unused = data.get("unused", {}) if isinstance(data, dict) else {}
    brief = norm(open(brief_p).read())
    bad, warn, seen = [], [], set()
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
    for num in sorted(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d+(?:\.\d+)?\b", brief))):
        if num not in text and num not in unused and len(num) > 1:
            warn.append("number/date %r in the brief is not covered by any rule" % num)
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
