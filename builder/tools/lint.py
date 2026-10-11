"""Structural lint for a Freya workflow file. Brief-independent.

    python3 tools/lint.py workflow.json [tools.json]

Exit 1 when something is wrong. Warnings (size) do not fail. Catches what the platform would silently drop or what
deadlocks a call: `tools` on a non-conversation node, `pre_actions` on a conversation node, passthrough nodes without a
final always-transition, unknown transition targets, nodes that cannot reach an end_call node or tool, null values, double braces
in code, mapping paths not starting with `data.`, and bank calls to any host other than the tool API's.
"""
import json, re, sys


def calls(node):
    for c in node.get("pre_actions", []) + node.get("tools", []):
        f = c.get("function", {})
        if f.get("handler") == "__function__:api_call":
            yield f.get("name"), c, f.get("parameters", {}).get("properties", {}).get("url", {}).get("default", "")


def code_strings(node):
    for c in node.get("pre_actions", []) + node.get("tools", []):
        f = c.get("function", {})
        p = f.get("parameters", {}).get("properties", {})
        if "code" in p:
            yield f.get("name"), p["code"].get("default", "")
        for h in ("pre_process_code", "post_process_code"):
            if c.get(h):
                yield "%s.%s" % (f.get("name"), h), c[h]


def lint(wf, base_url=None):
    bad, warn = [], []
    nodes = wf.get("nodes", {})
    if wf.get("initial_node") not in nodes:
        bad.append("initial_node %r is not a node" % wf.get("initial_node"))
    def has_null(x):
        if x is None:
            return True
        if isinstance(x, dict):
            return any(has_null(v) for v in x.values())
        if isinstance(x, list):
            return any(has_null(v) for v in x)
        return False
    if has_null(wf):
        bad.append("null value in workflow (the schema is strict; omit the key or use an empty string)")
    for name, n in nodes.items():
        t = n.get("node_type")
        if n.get("tools") and t != "conversation":
            bad.append("%s: tools on a %s node are silently dropped" % (name, t))
        if n.get("pre_actions") and t == "conversation":
            bad.append("%s: pre_actions on a conversation node are silently dropped" % name)
        for tr in n.get("transitions", []):
            if tr["target_node"] not in nodes and tr["target_node"] != "__previous__":
                bad.append("%s: transition to unknown node %s" % (name, tr["target_node"]))
        if n.get("max_turn_transition") and n["max_turn_transition"] not in nodes:
            bad.append("%s: max_turn_transition to unknown node" % name)
        if n.get("passthrough") and (not n.get("transitions") or n["transitions"][-1].get("condition", {}).get("operator") != "always"):
            bad.append("%s: passthrough node must end with an always transition" % name)
        if t == "end_call" and not n.get("terminal"):
            bad.append("%s: end_call node without terminal" % name)
        for label, src in code_strings(n):
            if "{{" in src or "}}" in src:
                bad.append("%s/%s: double brace inside code" % (name, label))
            try:
                compile(src, "<%s>" % label, "exec")
            except SyntaxError as e:
                bad.append("%s/%s: python syntax error: %s" % (name, label, e))
        for m in n.get("response_mapping", []) + [m for c in n.get("tools", []) for m in c.get("response_mapping", [])]:
            if not m.get("path", "").startswith("data."):
                bad.append("%s: response_mapping path %r should start with data." % (name, m.get("path")))
        for fname, c, url in calls(n):
            if base_url and not url.startswith(base_url):
                bad.append("%s: %s calls %r, outside the tool API" % (name, fname, url))
            if '"const"' in json.dumps(c.get("function", {}).get("parameters", {})):
                bad.append("%s: %s uses const; the engine bakes only default" % (name, fname))
    def can_end(n):
        return n.get("node_type") == "end_call" or any(t.get("function", {}).get("handler") == "__function__:end_call" for t in n.get("tools", []))
    ends = {k for k, n in nodes.items() if can_end(n)}
    reach, grew = set(ends), True
    while grew:
        grew = False
        for k, n in nodes.items():
            tg = [t["target_node"] for t in n.get("transitions", [])] + ([n["max_turn_transition"]] if n.get("max_turn_transition") else [])
            if k not in reach and any(x in reach for x in tg):
                reach.add(k); grew = True
    for k in nodes:
        if k not in reach:
            bad.append("%s cannot reach an end_call node or tool" % k)
    lines = json.dumps(wf, indent=1).count("\n") + 1
    if lines > 900:
        warn.append("workflow is %d lines pretty-printed; the target is about 600. Simplify." % lines)
    elif lines > 700:
        warn.append("workflow is %d lines pretty-printed; the target is about 600." % lines)
    return bad, warn, lines


if __name__ == "__main__":
    wf = json.load(open(sys.argv[1]))
    base = None
    if len(sys.argv) > 2:
        base = json.load(open(sys.argv[2]))["servers"][0]["url"].rstrip("/")
    bad, warn, lines = lint(wf, base)
    for w in warn:
        print("WARN", w)
    for b in bad:
        print("FAIL", b)
    print("lint:", "FAILED" if bad else "clean", "(%d lines, %d nodes)" % (lines, len(wf.get("nodes", {}))))
    sys.exit(1 if bad else 0)
