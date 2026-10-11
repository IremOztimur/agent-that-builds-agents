"""Static checks on a compiled workflow. The trust-boundary checks (G*) are the ones that must never be waived.

    python3 builder/lint.py <workflow.json> <openapi.json>

G1  every engine-run call to a protected operation sits behind a gate: each transition into its node tests the
    authorisation variable for 'granted' and nothing else
G2  no protected operation is a tool of a conversation node (the model can never call it)
G3  trusted state (see gates.TRUSTED_PREFIXES) is written only by the generated policy nodes in gates.WRITERS
G4  engine-run requests take body values only from customer_id, literals, or code-validated variables
S*  structure: no null, no double braces in code, passthrough nodes end in an unconditional transition,
    every node can reach an end_call node
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gates
from nodes import Api

VALIDATED_VARS = {"customer_id", "cand_field", "cand_answer", "prop_product", "prop_amount", "prop_date"}


def _calls(node):
    """(op, call) for every engine-run request in a node."""
    out = []
    for c in node.get("pre_actions", []):
        f = c.get("function", {})
        if f.get("handler") == "__function__:api_call":
            out.append((f["parameters"]["properties"]["url"]["default"].rsplit("/", 1)[-1], c))
    return out


def _codes(node):
    """(label, source) for every code string in a node: code steps, tools and hooks."""
    out = []
    for c in node.get("pre_actions", []) + node.get("tools", []):
        f = c.get("function", {})
        props = f.get("parameters", {}).get("properties", {})
        if "code" in props:
            out.append((f.get("name"), props["code"]["default"]))
        for hook in ("pre_process_code", "post_process_code"):
            if c.get(hook):
                out.append((f.get("name") + "." + hook, c[hook]))
    return out


def _vars_in(text):
    return set(re.findall(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}", text))


def lint(wf, api, protected):
    """`protected` maps a protected operation to the authorisation variable that gates it."""
    bad = []
    nodes = wf["nodes"]
    if "null" in json.dumps(wf).replace('"null"', ""):
        bad.append("S1 null value in workflow")
    incoming = {}
    for name, n in nodes.items():
        for t in n.get("transitions", []):
            incoming.setdefault(t["target_node"], []).append((name, t))
    for name, n in nodes.items():
        for op, call in _calls(n):
            if op in protected:
                ins = incoming.get(name, [])
                if wf["initial_node"] == name or not ins:
                    bad.append("G1 %s calls protected %s but is %s" % (name, op, "the initial node" if not ins or wf["initial_node"] == name else ""))
                for src, t in ins:
                    conds = t["condition"].get("conditions", [])
                    ok = t["condition"].get("logic") == "or" and conds and all(
                        c.get("variable") == protected[op] and c.get("operator") == "equals" and c.get("operand") == "granted" for c in conds)
                    if not ok:
                        bad.append("G1 transition %s -> %s is not gated on %s == granted" % (src, name, protected[op]))
            # G4
            body = call["function"]["parameters"]["properties"].get("body", {}).get("properties", {})
            for field, spec in body.items():
                for v in _vars_in(str(spec.get("default", ""))):
                    if v not in VALIDATED_VARS:
                        bad.append("G4 %s: body field %s of %s takes unvalidated variable %s" % (name, field, op, v))
        for t in n.get("tools", []):
            f = t.get("function", {})
            url = f.get("parameters", {}).get("properties", {}).get("url", {}).get("default", "")
            if url.rsplit("/", 1)[-1] in protected:
                bad.append("G2 conversation node %s lists protected tool %s" % (name, f.get("name")))
        for label, src in _codes(n):
            if "{{" in src or "}}" in src:
                bad.append("S2 double brace in code of %s/%s" % (name, label))
            writes_trusted = [p for p in gates.TRUSTED_PREFIXES if re.search(r"vars\[\s*['\"]" + re.escape(p), src)]
            if writes_trusted and name not in gates.WRITERS:
                bad.append("G3 %s/%s writes trusted state %s" % (name, label, writes_trusted))
        if n.get("passthrough") and n["transitions"][-1]["condition"].get("operator") != "always":
            bad.append("S3 passthrough node %s does not end with an always transition" % name)
    # S4: every node reaches an end_call node
    ends = {k for k, n in nodes.items() if n.get("node_type") == "end_call"}
    reach = set(ends)
    changed = True
    while changed:
        changed = False
        for k, n in nodes.items():
            targets = [t["target_node"] for t in n.get("transitions", [])] + ([n["max_turn_transition"]] if n.get("max_turn_transition") else [])
            if k not in reach and any(t in reach for t in targets):
                reach.add(k)
                changed = True
    for k in nodes:
        if k not in reach:
            bad.append("S4 node %s cannot reach an end_call node" % k)
    for src, ts in incoming.items():
        if src not in nodes:
            bad.append("S5 transition into unknown node %s" % src)
    return bad


if __name__ == "__main__":
    wf = json.load(open(sys.argv[1]))
    api = Api.load(sys.argv[2])
    import policy_a
    P = policy_a.POLICY
    problems = lint(wf, api, {P["account"]["op"]: P["account"]["auth_var"], P["promise"]["op"]: P["promise"]["auth_var"]})
    print("\n".join(problems) or "lint clean")
    sys.exit(1 if problems else 0)
