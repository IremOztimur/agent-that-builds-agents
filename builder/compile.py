"""Policy model + tool API file -> Freya workflow (identity path, M1 step 1).

    python3 builder/compile.py <openapi.json> [--no-controller]    writes eval/out/identity.workflow.json

`--no-controller` builds the same agent without the model's controller tool. It is a test fixture for the
"model skips the controller call" case: nothing may be verified and nothing may be read.
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gates
from nodes import Api, always, api_node, close_node, code_node, controller_tool, engine_call, hang_up, when

IDENTITY_TASK = """You are running a security check. You do not know why the bank is calling.

SECRECY: never say the words {secrecy}, and never mention an amount or why the bank is calling, not even to the customer. If asked what the call is about, say: "{secrecy_reply}"

THE CHECK: the system decides which question is pending and tells you what to say. Never judge an answer yourself.
- Whenever the customer gives an answer to a security question, CALL report_answer. Use field date_of_birth with the date as YYYY-MM-DD, whatever way the customer said it (a date given only as numbers is day, then month, then year), or field phone_last4 with exactly four digits. If the customer gives a number or date in parts, wait until you have all of it. If the customer corrects themselves, use the corrected value.
- Call report_answer at most once per message, and only when the customer gave an answer.
- After the tool result arrives, say exactly the line after SAY and nothing else, and call no tool.
- If the customer did not give an answer (a question, a comment), reply in one short sentence and repeat the pending question. Never answer for them.
SAY: {{{{say}}}}"""


def identity_cfg(ident):
    return {"questions": ident["questions"], "fields": [q["field"] for q in ident["questions"]], "swapped": ident["swapped"],
            "next_prefix": ident["next_prefix"], "wrong_prefix": ident["wrong_prefix"], "fallback": ident["fallback"],
            "max_unread": ident["max_unread"]}


def identity_node(name, policy, on_enter, with_controller=True):
    ident = policy["identity"]
    cfg = identity_cfg(ident)
    fields = [q["field"] for q in ident["questions"]]
    tool = controller_tool(
        "report_answer", gates.controller(cfg),
        "Reports the customer's answer to a security question. CALL it every time the customer gives an answer. It does not check the answer.",
        {"field": {"type": "string", "enum": fields, "description": "Which question the answer belongs to. One of: " + ", ".join(fields) + "."},
         "answer": {"type": "string", "description": "date_of_birth: the date as YYYY-MM-DD. phone_last4: the four digits."}})
    task = IDENTITY_TASK.format(secrecy=", ".join('"%s"' % w for w in ident["secrecy_words"]), secrecy_reply=ident["secrecy_reply"])
    return {"name": name, "node_type": "conversation", "on_enter": on_enter, "task_message": task,
            "tools": [tool] if with_controller else [], "max_node_turns": 30, "max_turn_transition": "close_unverified",
            "transitions": [when("verify_call", "The controller accepted a candidate answer", "go", "verify")]}


def compile_identity(policy, api, with_controller=True):
    ident, acct = policy["identity"], policy["account"]
    vop = ident["op"]
    cfg = identity_cfg(ident)
    req, res = ident["request"], ident["response"]
    verify = engine_call(api, vop, {req["field"]: "{{cand_field}}", req["answer"]: "{{cand_answer}}"})
    mapping = [{"path": "data." + res[k], "variable": v} for k, v in
               (("ok", "vf_ok"), ("verified", "vf_verified"), ("all", "vf_all"), ("left", "vf_left"), ("hint", "vf_hint"))]
    account = engine_call(api, acct["op"], {}, post=gates.POST_ACCOUNT)
    nodes = {
        "identity_open": identity_node("identity_open", policy, {"type": "tts", "text": policy["opening"]}, with_controller),
        "identity": identity_node("identity", policy, {"type": "tts", "text": "{{say}}"}, with_controller),
        "verify_call": api_node("verify_call", verify, mapping, [always("after_verify")]),
        "after_verify": code_node("after_verify", gates.after_verify(cfg), [
            when("gate_account", "The bank confirmed both answers", "id_state", "passed"),
            when("close_unverified", "The check failed", "id_state", "failed"),
            always("identity")]),
        "gate_account": code_node("gate_account", gates.gate_account(cfg), [
            when("fetch_account", "Authorised to read the account", acct["auth_var"], "granted"),
            always("close_unverified")]),
        "fetch_account": api_node("fetch_account", account,
                                  [{"path": "data.products_json", "variable": "products_json"}, {"path": "data.ok", "variable": "acct_ok"}],
                                  [always("after_account")]),
        "after_account": code_node("after_account", gates.after_account(
            {"product_words": acct["product_words"], "product_default": acct["product_default"], "line": acct["line"]}), [
            when("account_stated", "The account facts are ready", "acct_state", "ok"),
            always("close_account_error")]),
        "account_stated": {"name": "account_stated", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Thank you, you are verified. {{debt_line}}"},
                           "on_enter_first_entry_only": True,
                           "task_message": "The security check is done and you have stated the account facts. Reply in one short sentence. Call no tool.",
                           "max_node_turns": 5, "max_turn_transition": "hang_up", "transitions": []},
        "hang_up": hang_up(),
    }
    cl = policy["closings"]
    nodes["close_unverified"] = close_node("close_unverified", api, cl["unverified"]["outcome"], cl["unverified"]["reason"], cl["unverified"]["line"])
    nodes["close_account_error"] = close_node("close_account_error", api, cl["account_error"]["outcome"], cl["account_error"]["reason"], cl["account_error"]["line"])
    return {"initial_node": "identity_open", "system_prompt": policy["system_prompt"], "global_nodes": {}, "nodes": nodes}


if __name__ == "__main__":
    import policy_a
    api = Api.load(sys.argv[1])
    wf = compile_identity(policy_a.POLICY, api, with_controller="--no-controller" not in sys.argv)
    out = pathlib.Path(__file__).resolve().parent.parent / "eval" / "out"
    out.mkdir(parents=True, exist_ok=True)
    path = out / ("identity-nocontroller.workflow.json" if "--no-controller" in sys.argv else "identity.workflow.json")
    path.write_text(json.dumps(wf, indent=1))
    print("wrote", path, len(wf["nodes"]), "nodes")
