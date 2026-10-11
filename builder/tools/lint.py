"""Structural lint for a Freya workflow file. Brief-independent.

    python3 tools/lint.py workflow.json [tool API file]     (default: the one in inputs.json)

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


MAX_TURNS = 15       # most user turns one conversation node may spend


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
        if t == "conversation" and not n.get("max_turn_transition"):
            bad.append("%s: no max_turn_transition (max_node_turns defaults to 10 user turns and the cap does nothing without a target)" % name)
        if t == "conversation" and int(n.get("max_node_turns", 10)) > MAX_TURNS:
            bad.append("%s: max_node_turns is %s; at most %d, so a stuck loop ends in a few turns" % (name, n.get("max_node_turns"), MAX_TURNS))
        for es in n.get("extraction_schema", []):
            if "min_confidence" not in es:
                bad.append("%s: extraction variable %s has no min_confidence (the default 0.95 silently discards values)" % (name, es.get("name")))
        for tr in n.get("transitions", []):
            if tr.get("condition", {}).get("logic") == "and":
                bad.append("%s: a top-level condition group must use logic 'or'; nest an 'and' group inside it" % name)
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
    reference_rules(wf, nodes, bad, warn)
    lines = json.dumps(wf, indent=1).count("\n") + 1
    if lines > 900:
        warn.append("workflow is %d lines pretty-printed; the target is about 600. Simplify." % lines)
    elif lines > 700:
        warn.append("workflow is %d lines pretty-printed; the target is about 600." % lines)
    return bad, warn, lines


BLANKS_URL = re.compile(r"config\[['\"]url['\"]\]\s*=\s*(''|\"\")")


def chain_length(nodes, start):
    """Most passthrough nodes (code or api_request) one after another from `start`, following every outgoing transition."""
    def walk(k, seen):
        n = nodes.get(k, {})
        if not n.get("passthrough") or k in seen:
            return 0
        nxt = [t["target_node"] for t in n.get("transitions", [])] + ([n["passthrough_default_transition"]] if n.get("passthrough_default_transition") else [])
        return 1 + max([walk(x, seen | {k}) for x in nxt] or [0])
    return walk(start, set())


def reference_rules(wf, nodes, bad, warn):
    """What docs/workflow-format.md and docs/tools-and-code.md say, as checks."""
    if wf.get("context_variables"):
        warn.append("context_variables: a workflow saved over the API came back without this key (workflow-format.md). Put the values in the prompt with {{variable}}")
    for name, n in nodes.items():
        t = n.get("node_type")
        for c in n.get("pre_actions", []):
            if BLANKS_URL.search(c.get("pre_process_code") or ""):
                bad.append("%s: a node that runs on entry must make its call. Blanking the url in a pre_actions hook makes the platform log a failed api_call on every pass; "
                           "skip the node with a transition on a variable instead (tools-and-code.md, \"Use pre_actions when the call must always run\")" % name)
        if n.get("passthrough") and chain_length(nodes, name) >= 3 and not any(m.get("passthrough") and name in [x["target_node"] for x in m.get("transitions", [])] for m in nodes.values()):
            bad.append("%s starts a chain of %d passthrough nodes. Optional actions belong in one conversation node with several tools, not in a chain of passthrough nodes (tools-and-code.md)" % (name, chain_length(nodes, name)))
        if "loop_prompt" in n:
            bad.append("%s: loop_prompt is rejected by the platform (\"Unrecognized key\") although the docs list it. Put what must change after the first turn into task_message" % name)
        if n.get("extraction_prompt") or any(e.get("extraction_prompt") and "{{extractor.speech}}" not in e["extraction_prompt"] for e in n.get("extraction_schema", [])):
            for e in n.get("extraction_schema", []):
                if e.get("extraction_prompt") and "{{extractor.speech}}" not in e["extraction_prompt"]:
                    bad.append("%s: extraction_prompt of %s replaces the whole template and must contain {{extractor.speech}}, {{extractor.conversation.last-10}}, {{extractor.type_preamble}} and {{extractor.variables_list}}" % (name, e.get("name")))
        for e in n.get("extraction_schema", []):
            if "date" in str(e.get("name", "")).lower() and e.get("type") == "string" and not e.get("enum_values"):
                warn.append("%s: %s looks like a date but is typed string; declare dates as type \"date\" so the extractor gets today's date" % (name, e.get("name")))
        if t == "end_call":
            term = n.get("terminal", {}).get("function", {}).get("parameters", {}).get("properties", {})
            if (n.get("on_enter") or {}).get("type") not in (None, "silent") and term.get("message_mode", {}).get("default") == "none":
                bad.append("%s: an end_call node with an on_enter line and message_mode none hangs up silently; put the sentence in spoken_message and set on_enter to silent" % name)
        if re.search(r"\bnode\b", (n.get("task_message") or "")):
            warn.append("%s: task_message talks about nodes; the model does not know about nodes and narrates steps that have not happened" % name)
        for tr in n.get("transitions", []):
            for grp in tr.get("condition", {}).get("conditions", []):
                for v in ([grp] if "variable" in grp else grp.get("conditions", [])):
                    ops = {str(x.get("operand")) for x in ([c for g in tr["condition"]["conditions"] for c in ([g] if "variable" in g else g.get("conditions", []))]) if x.get("variable") == v.get("variable") and x.get("operator") == "equals"}
                    if ("true" in ops) != ("True" in ops):
                        warn.append("%s: transition to %s tests %s against only one spelling of a boolean; test both \"true\" and \"True\" or use a string value" % (name, tr["target_node"], v.get("variable")))
        for c in n.get("tools", []):
            if "call" not in str(c.get("function", {}).get("description", "")).lower():
                warn.append("%s: tool %s has no \"CALL it when ...\" trigger in its description; the model may talk about the action instead of taking it" % (name, c.get("function", {}).get("name")))


if __name__ == "__main__":
    wf = json.load(open(sys.argv[1]))
    base = None
    try:
        sys.path.insert(0, __import__("os").path.dirname(__file__))
        import inputs
        api = sys.argv[2] if len(sys.argv) > 2 else str(inputs.tools_path())
        base = json.load(open(api))["servers"][0]["url"].rstrip("/")
    except Exception:
        pass
    bad, warn, lines = lint(wf, base)
    for w in warn:
        print("WARN", w)
    for b in bad:
        print("FAIL", b)
    print("lint:", "FAILED" if bad else "clean", "(%d lines, %d nodes)" % (lines, len(wf.get("nodes", {}))))
    sys.exit(1 if bad else 0)
