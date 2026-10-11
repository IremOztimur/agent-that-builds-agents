"""M0 probe: can code decide the agent's next move, and can a bank call be stubbed inside the workflow?

    source env.sh && python3 dev/probes/probe_controller.py

Questions it answers, from the call's event log:
1. Can the dialogue model call a `code_exec` tool, and how do its arguments reach the code?
2. Does a transition on a variable that the code wrote fire in the same turn (ping-pong between two nodes)?
3. Is a `{{var}}` in a fixed `on_enter` line resolved from a variable the code wrote one step earlier?
4. Does a structured value passed as a call variable arrive in `vars`?
5. How long does one such turn take?
"""
import json, pathlib, sys, time

KIT = pathlib.Path(__file__).resolve().parents[2] / "builder" / "kit"
sys.path.insert(0, str(KIT))
import freya

CODE = """
try:
    try:
        a_local = act
    except NameError:
        a_local = 'NO_LOCAL'
    ks = [str(k) for k in vars.keys()]
    vars['dbg_keys'] = ','.join(sorted(k for k in ks if 'report' in k or k in ('act', 'detail', 'fixture')))[:800]
    vars['dbg_local'] = str(a_local)
    vars['dbg_fixture_type'] = type(vars.get('fixture')).__name__
    a = vars.get('act') or vars.get('report_turn_args.act') or a_local
    n = int(float(vars.get('turn_n') or 0)) + 1
    vars['turn_n'] = n
    vars['move_text'] = 'Move ' + str(n) + ', you reported ' + str(a) + '. Please say the next thing.'
    vars['ctl'] = 'b' if str(vars.get('ctl') or 'a') == 'a' else 'a'
except Exception as e:
    vars['dbg_err'] = str(e)[:300]
"""

TASK = ("You are a test harness. Every time the user says anything, CALL report_turn at once with act set to one of "
        "greet, refuse, agree and detail set to the user's words. Say nothing yourself. Call one tool per message.")


def report_tool():
    return {"type": "function", "config": {"timeoutMs": 10000},
            "function": {"name": "report_turn", "handler": "__function__:code_exec",
                         "description": "Reports what the user just did. CALL it after every user message.",
                         "parameters": {"type": "object", "properties": {
                             "code": {"type": "string", "default": CODE},
                             "timeout_ms": {"type": "number", "default": 10000},
                             "act": {"type": "string", "enum": ["greet", "refuse", "agree"], "description": "One of: greet, refuse, agree."},
                             "detail": {"type": "string", "description": "The user's words."}},
                             "required": ["act"]}}}


def node(name, other, flag, first_line):
    return {"name": name, "node_type": "conversation", "on_enter": {"type": "tts", "text": first_line},
            "task_message": TASK, "tools": [report_tool()], "max_node_turns": 30, "max_turn_transition": "bye",
            "transitions": [{"target_node": other, "description": "the code chose the next move",
                             "condition": {"logic": "or", "conditions": [{"variable": "ctl", "operator": "equals", "operand": flag}]}}]}


WF = {"initial_node": "main_a", "system_prompt": "You are a test harness. Follow the task exactly.", "global_nodes": {},
      "test_variables": {"customer_id": "c_test", "now": "2026-10-14T11:00"},
      "nodes": {
          "main_a": node("main_a", "main_b", "b", "Ready."),
          "main_b": node("main_b", "main_a", "a", "{{move_text}}"),
          "bye": {"name": "bye", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
                  "terminal": {"type": "function", "function": {"name": "ended", "handler": "__function__:end_call",
                                                                "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}}}
WF["nodes"]["main_a"]["on_enter_first_entry_only"] = True
# second visit of main_a must speak the move as well
WF["nodes"]["main_a2"] = dict(node("main_a2", "main_b", "b", "{{move_text}}"))
WF["nodes"]["main_b"]["transitions"][0]["target_node"] = "main_a2"

if __name__ == "__main__":
    print("dry run:", str(freya.validate_workflow("probe", WF))[:200])
    r = freya.save_workflow("probe", WF, state_file=str(KIT / ".freya-agents.json"))
    print(r)
    variables = {"customer_id": "c_test", "now": "2026-10-14T11:00", "fixture": {"products": [{"product_id": "p1", "past_due": 420.0}], "dob": "1988-03-14"}}
    cid = None
    for msg in ("hello", "no, I will not", "ok fine, yes"):
        body = {"workflowId": r["workflow_id"], "message": msg, "customerVariables": variables}
        if cid: body["callId"] = cid
        t0 = time.time()
        try:
            out = freya.api("POST", "/api/v2/chat/message", body)
            cid = out.get("callId", cid)
            print(f"USER: {msg}\nAGENT ({time.time() - t0:.1f} s): {out.get('response')}")
        except Exception as e:
            print("ERR", str(e)[:400])
    if cid:
        call = freya.get_call(cid)
        last_vt = None
        for m in call["messages"]:
            if m["role"] != "system":
                print(m["role"].upper(), m.get("nodeId"), "|", str(m["message"])[:300]); continue
            try: ev = json.loads(m["message"])
            except Exception: print("SYS", m["message"][:300]); continue
            if ev.get("event") == "route_evaluated":
                last_vt = ev.get("variable_table") or last_vt
                print("ROUTE", ev.get("from_node"), "->", ev.get("target"), "matched", ev.get("matched"))
            else:
                print("SYS", json.dumps(ev)[:700])
        if last_vt:
            keep = {k: v for k, v in last_vt.items() if k.startswith(("dbg_", "report_turn", "ctl", "turn_n", "move_text", "fixture", "act", "detail")) and "header" not in k}
            print("VARS", json.dumps(keep, indent=1, default=str)[:3000])
        try: freya.api("POST", "/api/v2/chat/end", {"callId": cid})
        except Exception as e: print("end:", str(e)[:200])
