"""Drive one scripted chat against a published workflow slot and show what happened.

    cd build-the-builder_pack && source env.sh
    python3 ../eval/chat_script.py save <slot> <workflow.json>          dry run, save, publish, read back and diff
    python3 ../eval/chat_script.py run <slot> <CASE> "msg" "msg" ...    scripted chat as the practice customer CASE

Prints: the agent's replies, every bank call the engine made (args and result), node transitions, the trusted
variables at the end, and the bank's ledger for the session.
"""
import json, pathlib, sys, time

KIT = pathlib.Path(__file__).resolve().parents[1] / "build-the-builder_pack"
sys.path.insert(0, str(KIT)); sys.path.insert(0, str(KIT / "tools"))
import freya
from score import http

STATE = str(KIT / ".freya-agents.json")
SHOW = ("id_state", "idok_", "auth_", "acct_", "go", "say", "cand_", "vf_", "debt_line", "negotiate", "prop_", "conf_", "promise_", "pr_", "call.")


def strip(x):
    """Drop what the platform removes silently, so a read-back diff only shows real differences."""
    return x


def save(slot, path):
    wf = json.load(open(path))
    print("dry run:", freya.validate_workflow(slot, wf))
    r = freya.save_workflow(slot, wf, state_file=STATE)
    print("saved:", r)
    got = freya.api("GET", "/api/v2/workflow/" + r["workflow_id"], workspaceId=freya.workspace_id())["workflow"]["workflow"]
    lost = [n for n in wf["nodes"] if n not in got["nodes"]]
    print("nodes sent", len(wf["nodes"]), "stored", len(got["nodes"]), "missing", lost)
    for name, n in wf["nodes"].items():
        g = got["nodes"].get(name, {})
        for key in ("tools", "pre_actions", "transitions", "response_mapping"):
            if len(n.get(key, [])) != len(g.get(key, [])):
                print("DIFF", name, key, "sent", len(n.get(key, [])), "stored", len(g.get(key, [])))
        for key in ("on_enter", "passthrough", "node_type", "task_message"):
            if n.get(key) != g.get(key):
                print("DIFF", name, key)
    return r


def run(slot, case, msgs):
    wid = json.load(open(STATE))[slot]["workflow_id"]
    s = http("/v1/practice/sessions", {"case": case})["variables"]
    cid = None
    for msg in msgs:
        body = {"workflowId": wid, "message": msg, "customerVariables": s}
        if cid:
            body["callId"] = cid
        t0 = time.time()
        try:
            out = freya.api("POST", "/api/v2/chat/message", body)
            cid = out.get("callId", cid)
            print("USER :", msg, "\nAGENT: (%.1fs)" % (time.time() - t0), out.get("response"))
            if out.get("endedByAgent"):
                print("   [call ended by agent]")
                break
        except Exception as e:
            print("USER :", msg, "\nERR", str(e)[:300])
            break
    last = None
    if cid:
        time.sleep(2)
        call = freya.get_call(cid)
        print("--- events; ended:", call.get("endedReason"))
        for m in call["messages"]:
            if m["role"] != "system":
                continue
            try:
                ev = json.loads(m["message"])
            except Exception:
                continue
            e = ev.get("event")
            if e == "node_enter":
                print("   NODE", ev.get("from_node"), "->", ev.get("node"))
            elif e == "function_call_start":
                a = ev.get("args") or {}
                print("   CALL", ev.get("function"), json.dumps(a.get("body", a.get("params", "")))[:200])
            elif e in ("function_call_complete", "function_call_error"):
                print("   RSLT", json.dumps(ev.get("result", ev.get("error")))[:300])
            elif e == "error":
                print("   ERROR", json.dumps(ev)[:300])
            elif e == "route_evaluated":
                last = ev.get("variable_table") or last
        if last:
            print("   VARS", json.dumps({k: (v.get("value") if isinstance(v, dict) else v) for k, v in last.items() if k.startswith(SHOW)}, default=str)[:900])
        try:
            freya.api("POST", "/api/v2/chat/end", {"callId": cid})
        except Exception:
            pass
    L = http("/v1/practice/ledger/" + s["customer_id"])
    print("LEDGER outcome", L["outcome"], L["reason"], "| calls:", [(c["tool"], c["result"].get("ok"), c["result"].get("error")) for c in L["calls"]])
    return L


if __name__ == "__main__":
    if sys.argv[1] == "save":
        save(sys.argv[2], sys.argv[3])
    else:
        run(sys.argv[2], sys.argv[3], sys.argv[4:])
