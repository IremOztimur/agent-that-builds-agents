"""Policy model + tool API file -> Freya workflow (identity path, M1 step 1).

    python3 builder/compile.py <openapi.json> [--no-controller]    writes eval/out/identity.workflow.json

`--no-controller` builds the same agent without the model's controller tool. It is a test fixture for the
"model skips the controller call" case: nothing may be verified and nothing may be read.
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gates
from nodes import Api, always, api_node, close_node, code_node, controller_tool, engine_call, hang_up, when




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
    task = policy["prompts"]["identity"].replace("SECRECY_WORDS", ", ".join('"%s"' % w for w in ident["secrecy_words"])).replace("SECRECY_REPLY", ident["secrecy_reply"])
    return {"name": name, "node_type": "conversation", "on_enter": on_enter, "task_message": task,
            "tools": [tool] if with_controller else [], "max_node_turns": 30, "max_turn_transition": "close_unverified",
            "transitions": [when("verify_call", "The controller accepted a candidate answer", "go", "verify")]}


def account_cfg(policy):
    a = policy["account"]
    return {"product_words": a["product_words"], "product_default": a["product_default"], "line": a["line"], "first_ask": a["first_ask"],
            "floor_fields": a["floor_fields"], "floor_names": a["floor_names"], "bands": a["bands"], "holidays": a["holidays"]}


def gate_cfg(policy):
    return {"fields": [q["field"] for q in policy["identity"]["questions"]], "holidays": policy["account"]["holidays"],
            "max_attempts": policy["promise"]["max_attempts"]}





def promise_cfg(policy):
    prm = policy["promise"]
    return {"lines": prm["lines"], "turn_key": prm["turn_key"], "holidays": policy["account"]["holidays"]}


def negotiate_node(policy):
    prm = policy["promise"]
    cfg = promise_cfg(policy)
    prop = controller_tool(
        "report_proposal", gates.proposal(cfg),
        "Reports an amount and a date the customer agreed to pay. CALL it whenever an amount and a date are agreed. It does not record anything.",
        {"amount": {"type": "number", "description": "The amount the customer agreed to pay, as a number, for example 637.5."},
         "date": {"type": "string", "description": "The payment date as YYYY-MM-DD."}})
    conf = controller_tool(
        "report_confirmation", gates.confirmation(cfg),
        "Reports the customer's answer to your read-back of the amount and the date. CALL it only after the customer replied to the read-back.",
        {"decision": {"type": "string", "enum": ["yes", "no"], "description": "yes only if the customer clearly confirmed the read-back."}})
    return {"name": "negotiate", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Thank you, you are verified. {{debt_line}}"},
            "on_enter_first_entry_only": True, "task_message": policy["prompts"]["negotiate"], "tools": [prop, conf],
            "max_node_turns": 40, "max_turn_transition": "close_refused",
            "transitions": [when("gate_promise", "The customer confirmed the stored proposal", "go", "promise")]}


def compile_identity(policy, api, with_controller=True):
    ident, acct, prm = policy["identity"], policy["account"], policy["promise"]
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
        "after_account": code_node("after_account", gates.after_account(account_cfg(policy)), [
            when("negotiate", "The account facts are ready", "acct_state", "ok"),
            always("close_account_error")]),
        "negotiate": negotiate_node(policy),
        "gate_promise": code_node("gate_promise", gates.gate_promise(gate_cfg(policy)), [
            when("create_promise_call", "Authorised to record the promise", prm["auth_var"], "granted"),
            always("close_service_error")]),
        "create_promise_call": api_node("create_promise_call", engine_call(api, prm["op"], {
            prm["request"]["product_id"]: "{{prop_product}}", prm["request"]["amount"]: ("{{prop_amount}}", "number"), prm["request"]["date"]: "{{prop_date}}"}),
            [{"path": "data." + prm["response"]["ok"], "variable": "pr_ok"}, {"path": "data." + prm["response"]["id"], "variable": "pr_id"}],
            [always("after_promise")]),
        "after_promise": code_node("after_promise", gates.after_promise({"max_attempts": prm["max_attempts"]}), [
            when("close_promise", "The bank recorded the promise", "promise_state", "recorded"),
            when("gate_promise", "The first try failed; one more try is allowed", "promise_state", "retry"),
            always("close_service_error")]),
        "hang_up": hang_up(),
    }
    cl = policy["closings"]
    for key, name in (("promise", "close_promise"), ("service_error", "close_service_error"), ("refused", "close_refused")):
        nodes[name] = close_node(name, api, cl[key]["outcome"], cl[key]["reason"], cl[key]["line"])
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
