"""Lint, save (create or update in place), publish and read back a workflow. Brief-independent.

    python3 tools/publish.py workflow.json            prints {"workflow_id", "agent_id"}

Uses freya.save_workflow with the slot from $BUILDER_SLOT and the state file $BUILDER_SLOT_STATE, so repeated calls
update the same workflow instead of filling the workspace. Refuses to publish a workflow that fails lint.
"""
import json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import freya, lint, inputs

wf = json.load(open(sys.argv[1]))
base = json.load(open(inputs.tools_path()))["servers"][0]["url"].rstrip("/")
bad, warn, lines = lint.lint(wf, base)
for w in warn:
    print("WARN", w)
if bad:
    print("\n".join("FAIL " + b for b in bad))
    sys.exit("not published: lint failed")
print("dry run:", freya.validate_workflow("dry", wf))
slot, state = os.environ.get("BUILDER_SLOT", "dev"), os.environ.get("BUILDER_SLOT_STATE", str(HERE.parent / ".slots.json"))
r = freya.save_workflow(slot, wf, state_file=state)
got = freya.api("GET", "/api/v2/workflow/" + r["workflow_id"], workspaceId=freya.workspace_id())["workflow"]["workflow"]
for name, n in wf["nodes"].items():
    g = got["nodes"].get(name)
    if g is None:
        print("READBACK missing node", name); continue
    for key in ("tools", "pre_actions", "transitions", "response_mapping", "extraction_schema"):
        if len(n.get(key, [])) != len(g.get(key, [])):
            print("READBACK %s.%s: sent %d, stored %d (the platform dropped something)" % (name, key, len(n.get(key, [])), len(g.get(key, []))))
log = json.load(open(HERE.parent / "published.json")) if (HERE.parent / "published.json").exists() else []
(HERE.parent / "versions").mkdir(exist_ok=True)
fname = "versions/pub-%d.json" % (len(log) + 1)
json.dump(wf, open(HERE.parent / fname, "w"))
log.append({"seq": len(log) + 1, "file": fname})
json.dump(log, open(HERE.parent / "published.json", "w"))
print(json.dumps({"workflow_id": r["workflow_id"], "agent_id": r["agent_id"], "lines": lines}))
