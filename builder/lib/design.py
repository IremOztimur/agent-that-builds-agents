"""Phase 1 gate on design.json: every live rule has a mechanism that exists in the workflow, and hard rules are never prompt-only."""
import json, re

LIVE = ("decided", "proposed", "unresolved")
HARD = ("gate", "calc", "state")
COUNTED = re.compile(r"\d|\b(once|twice|thrice|times|attempts?)\b", re.I)
DENSITY = 8        # most prompt-only rules the model is shown in one node
SIZE = 1000        # most lines of workflow.json (indent 2)


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
    shown = {}                                       # node -> live rules that only the prompt of that node carries
    text = _norm(" ".join(_strings(wf)))
    for r in rules:
        if r.get("status") not in LIVE:
            continue
        row = row_of.get(r["id"])
        if row is None:
            bad.append("rule %s has no row in design.json" % r["id"])
            continue
        if row["mechanism"] == "prompt" and (r.get("class") in HARD or r.get("kind") in ("gate", "limit", "allowed_set") or COUNTED.search(r.get("quote", ""))):
            bad.append("rule %s (%s) is prompt-only but is a hard rule: limits, windows, amounts and every counter must be structure or code" % (r["id"], r.get("class")))
        if row["mechanism"] == "prompt":
            nodes = [n for n in wf["nodes"] if n in str(row.get("where", ""))]
            if not nodes and "system prompt" not in str(row.get("where", "")).lower().replace("_", " "):
                bad.append("rule %s is carried by a prompt but `where` names neither a node of workflow.json nor system_prompt" % r["id"])
            for n in nodes:
                shown.setdefault(n, []).append(r["id"])
        if r.get("kind") == "wording" and _norm(r.get("wording", "")) not in text:
            bad.append("rule %s mandates exact wording, which is not in workflow.json: %r" % (r["id"], str(r.get("wording"))[:80]))
    for n, ids in shown.items():
        if len(ids) > DENSITY:
            bad.append("node %s shows the model %d rules (%s); at most %d: split the node by state, or settle the interplay in code and show conclusions" % (n, len(ids), ", ".join(ids), DENSITY))
    lines = len(json.dumps(wf, indent=2).splitlines())
    if lines > SIZE:
        bad.append("workflow.json is %d lines (indent 2); the limit is %d. Remove nodes or prompt text that no rule needs" % (lines, SIZE))
    return bad


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)
