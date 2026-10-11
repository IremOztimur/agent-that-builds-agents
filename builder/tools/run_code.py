"""Run one code snippet of the workflow locally with given variables. Brief-independent.

    python3 tools/run_code.py workflow.json <node-or-tool name> '{"var": "value"}' [--params '{"arg": 1}'] [--hook pre|post] [--config '{...}'] [--result '{...}']

Finds a code node's code, a code_exec tool's code, or a tool's pre_process_code / post_process_code (--hook) and executes
it the way the platform does: `vars` (dict), `params` (the model's arguments), `config` (the request, pre hook) or
`result` (the answer, post hook). Prints the variables, config and result afterwards. Use it to test calculations,
limits and counters with exact inputs; write the expected outputs from the rules BEFORE you read the code.
"""
import json, sys


def find(wf, name, hook):
    for nname, n in wf["nodes"].items():
        for c in n.get("pre_actions", []) + n.get("tools", []):
            f = c.get("function", {})
            if nname == name or f.get("name") == name:
                if hook:
                    return c.get(hook + "_process_code")
                p = f.get("parameters", {}).get("properties", {})
                if "code" in p:
                    return p["code"]["default"]
    return None


if __name__ == "__main__":
    wf = json.load(open(sys.argv[1]))
    name = sys.argv[2]
    vars_ = json.loads(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else {}
    opt = {}
    rest = sys.argv[3:]
    for i, a in enumerate(rest):
        if a.startswith("--") and i + 1 < len(rest):
            opt[a[2:]] = rest[i + 1]
    src = find(wf, name, opt.get("hook"))
    if not src:
        sys.exit("no code found for %r" % name)
    g = {"vars": vars_, "params": json.loads(opt.get("params", "{}")), "config": json.loads(opt.get("config", "{}")), "result": json.loads(opt.get("result", "{}"))}
    exec(compile(src, "<%s>" % name, "exec"), g)
    print(json.dumps({"vars": g["vars"], "config": g["config"], "result": g["result"]}, indent=1, default=str))
