"""Scripted chat against the published workflow of this slot, with the tool calls and routing shown. Brief-independent.

    python3 tools/chat.py vars.json "first customer message" "second message" ...

vars.json holds the call variables (for example customer_id, names, now). Unknown customers are refused by the bank, so
use this for the conversation up to the first bank answer, and for checking which tool is called with which arguments.
The first message starts the call; the fixed opening line of the first node may not be spoken in this test route.
"""
import json, os, pathlib, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import freya

slot, state = os.environ.get("BUILDER_SLOT", "dev"), os.environ.get("BUILDER_SLOT_STATE", str(HERE.parent / ".slots.json"))
wid = json.load(open(state))[slot]["workflow_id"]
variables = json.load(open(sys.argv[1]))
cid = None
for msg in sys.argv[2:]:
    body = {"workflowId": wid, "message": msg, "customerVariables": variables}
    if cid:
        body["callId"] = cid
    t0 = time.time()
    try:
        out = freya.api("POST", "/api/v2/chat/message", body)
    except Exception as e:
        print("USER :", msg, "\nERR", str(e)[:200]); break
    cid = out.get("callId", cid)
    print("USER :", msg, "\nAGENT: (%.1fs)" % (time.time() - t0), out.get("response"))
    if out.get("endedByAgent"):
        break
if cid:
    time.sleep(2)
    last = None
    print("--- events")
    for m in freya.get_call(cid)["messages"]:
        if m["role"] != "system":
            continue
        try:
            ev = json.loads(m["message"])
        except Exception:
            continue
        e = ev.get("event")
        if e == "node_enter":
            print("  node", ev.get("from_node"), "->", ev.get("node"))
        elif e == "function_call_start":
            a = ev.get("args") or {}
            print("  call", ev.get("function"), json.dumps(a.get("body", a.get("params", "")))[:220])
        elif e in ("function_call_complete", "function_call_error"):
            print("  result", json.dumps(ev.get("result", ev.get("error")))[:260])
        elif e == "error":
            print("  ERROR", json.dumps(ev)[:260])
        elif e == "route_evaluated":
            last = ev.get("variable_table") or last
    if last:
        keep = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in last.items() if not k.startswith(("system", "call.")) and "header" not in k}
        print("  variables:", json.dumps(keep, default=str)[:1500])
    try:
        freya.api("POST", "/api/v2/chat/end", {"callId": cid})
    except Exception:
        pass
