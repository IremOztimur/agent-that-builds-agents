"""Phase 1 gate on design.json: every live rule has a mechanism that exists in the workflow, and hard rules are never prompt-only."""
import json, re

LIVE = ("decided", "proposed", "unresolved")
HARD = ("gate", "calc", "state")
COUNTED = re.compile(r"\d|\b(once|twice|thrice|times|attempts?)\b", re.I)


def check(work):
    """Problems with design.json. Hard rules (gate, calc, state, or any rule that names a number or a count) must be structure or code."""
    try:
        design = json.load(open(work / "design.json"))
        rules = json.load(open(work / "rules.json"))["rules"]
        wf = json.load(open(work / "workflow.json"))
    except Exception as e:
        return ["design.json, rules.json or workflow.json cannot be read: %s" % e]
    names = set(wf["nodes"])
    for n in wf["nodes"].values():
        for t in n.get("tools", []) + n.get("pre_actions", []):
            names.add(t.get("function", {}).get("name", ""))
    for t in wf.get("tools", []):
        names.add(t.get("function", {}).get("name", ""))
    names.discard("")
    row_of, bad = {}, []
    for row in design.get("rows", []):
        if row.get("mechanism") not in ("structure", "code", "prompt"):
            bad.append("design row %s: mechanism must be structure, code or prompt" % row.get("rules") or row.get("rule"))
        if row.get("mechanism") != "prompt" and not any(nm in str(row.get("where", "")) for nm in names):
            bad.append("design row %s: `where` names no node or tool of workflow.json" % (row.get("rules") or row.get("rule")))
        for rid in row.get("rules", []) + ([row["rule"]] if row.get("rule") else []):
            row_of[rid] = row
    for r in rules:
        if r.get("status") not in LIVE:
            continue
        row = row_of.get(r["id"])
        if row is None:
            bad.append("rule %s has no row in design.json" % r["id"])
        elif row["mechanism"] == "prompt" and (r.get("class") in HARD or COUNTED.search(r.get("quote", ""))):
            bad.append("rule %s (%s) is prompt-only but is a hard rule: limits, windows, amounts and every counter must be structure or code" % (r["id"], r.get("class")))
    return bad
