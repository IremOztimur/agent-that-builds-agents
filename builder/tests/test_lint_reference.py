"""Offline checks that the lint holds a workflow to what the platform docs say. Run: python3 builder/tests/test_lint_reference.py"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import lint

ALWAYS = [{"target_node": "next", "description": "d", "condition": {"operator": "always"}}]
BYE = {"node_type": "end_call", "transitions": [], "terminal": {"function": {"name": "bye", "handler": "__function__:end_call", "parameters": {"properties": {"message_mode": {"default": "custom"}}}}}}


def call(name, hook=""):
    c = {"type": "function", "function": {"name": name, "handler": "__function__:api_call", "parameters": {"properties": {"url": {"default": "https://x/y"}}}}}
    if hook:
        c["pre_process_code"] = hook
    return c


def pas(target, **kw):
    return {"node_type": "api_request", "passthrough": True, "passthrough_default_transition": target,
            "transitions": [{"target_node": target, "description": "d", "condition": {"operator": "always"}}], **kw}


def wf(nodes):
    return {"initial_node": "a", "nodes": {**nodes, "bye": BYE}}


def problems(w):
    return lint.lint(w, "https://x")


def has(items, text):
    return any(text in i for i in items)


conv = {"node_type": "conversation", "task_message": "t", "max_node_turns": 10, "max_turn_transition": "bye", "transitions": ALWAYS and [{"target_node": "bye", "description": "d", "condition": {"operator": "always"}}]}

# a node that runs on entry must make its call
bad, _, _ = problems(wf({"a": pas("bye", pre_actions=[call("add_note", "config['url'] = ''")])}))
assert has(bad, "must make its call"), bad
bad, _, _ = problems(wf({"a": pas("bye", pre_actions=[call("get_account")])}))
assert not has(bad, "must make its call"), bad
# a blocking hook on a tool the model calls is the legitimate use and stays allowed
bad, _, _ = problems(wf({"a": {**conv, "tools": [call("create_promise", "config['url'] = ''")]}}))
assert not has(bad, "must make its call"), bad

# no long chain of passthrough nodes
chain = {"a": pas("b"), "b": pas("c"), "c": pas("bye")}
assert has(problems(wf(chain))[1], "chain of 3"), problems(wf(chain))[1]          # a warning: a sequence of needed calls is legitimate
assert not has(problems(wf(chain))[0], "chain of")
assert not has(problems(wf({"a": pas("b"), "b": pas("bye")}))[1], "chain of")

# platform facts from the docs
assert has(problems(wf({"a": {**conv, "loop_prompt": "x"}}))[0], "loop_prompt")
silent = {**BYE, "on_enter": {"type": "tts", "text": "bye"}, "terminal": {"function": {"name": "bye", "handler": "__function__:end_call", "parameters": {"properties": {"message_mode": {"default": "none"}}}}}}
assert has(problems({"initial_node": "a", "nodes": {"a": conv, "bye": silent}})[0], "hangs up silently")
ex = {**conv, "extraction_schema": [{"name": "x", "type": "string", "min_confidence": 0.7, "extraction_prompt": "just extract"}]}
assert has(problems(wf({"a": ex}))[0], "{{extractor.speech}}")
dt = {**conv, "extraction_schema": [{"name": "pay_date", "type": "string", "min_confidence": 0.7}]}
assert has(problems(wf({"a": dt}))[1], "declare dates")
print("ok: lint reference")
