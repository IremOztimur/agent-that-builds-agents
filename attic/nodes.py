"""Freya workflow building blocks. Brief-independent: nothing in here names a rule, a value or an outcome.

Shapes follow build-the-builder_pack/docs/workflow-format.md and tools-and-code.md.
"""
import json


class Api:
    """The tool API file: operations, body fields, allowed values, base URL."""

    def __init__(self, spec):
        self.spec = spec
        self.base = spec["servers"][0]["url"].rstrip("/")

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls(json.load(f))

    def ops(self):
        return [p.lstrip("/") for p in self.spec["paths"]]

    def body(self, op):
        return self.spec["paths"]["/" + op]["post"]["requestBody"]["content"]["application/json"]["schema"]

    def fields(self, op):
        return list(self.body(op).get("properties", {}))

    def enum(self, op, field):
        return self.body(op)["properties"][field].get("enum")

    def url(self, op):
        return self.base + "/" + op


def always(target):
    return {"target_node": target, "description": "always", "condition": {"operator": "always"}}


def eq(var, *values):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": v} for v in values]}


def when(target, description, var, *values):
    return {"target_node": target, "description": description, "condition": eq(var, *values)}


def _http_params(url):
    return {"url": {"type": "string", "default": url},
            "method": {"type": "string", "default": "POST"},
            "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}}}


def engine_call(api, op, fields, retries=0, post=""):
    """A request the engine runs on node entry. Every body value is a baked default: a literal or a {{var}}.

    `fields` maps a body field of the tool API to its default. A field the API does not know is a build error."""
    known = api.fields(op)
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    for name, spec in fields.items():
        if name not in known:
            raise ValueError("%s has no field %s in the tool API" % (op, name))
        default, typ = spec if isinstance(spec, tuple) else (spec, "string")
        props[name] = {"type": typ, "default": default}
    params = _http_params(api.url(op))
    params["body"] = {"type": "object", "properties": props, "required": []}
    call = {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries},
            "function": {"name": op, "handler": "__function__:api_call", "description": op,
                         "parameters": {"type": "object", "properties": params}}}
    if post:
        call["post_process_code"] = post
    return call


def api_node(name, call, mapping, transitions, line=""):
    """Passthrough node that runs one engine request, then routes. Ends with an always transition."""
    return {"name": name, "node_type": "api_request", "passthrough": True,
            "passthrough_default_transition": transitions[-1]["target_node"],
            "on_enter": {"type": "tts", "text": line} if line else {"type": "silent"},
            "disable_inactivity_monitor": True, "suppress_tool_results": True,
            "pre_actions": [call], "response_mapping": mapping, "transitions": transitions}


def code_node(name, code, transitions):
    """Passthrough node that runs policy code. The last transition must be unconditional."""
    if transitions[-1]["condition"].get("operator") != "always":
        raise ValueError("code node %s must end with an always transition" % name)
    return {"name": name, "node_type": "code", "passthrough": True,
            "passthrough_default_transition": transitions[-1]["target_node"], "on_enter": {"type": "silent"},
            "disable_inactivity_monitor": True,
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec",
                             "parameters": {"type": "object", "properties": {
                                 "code": {"type": "string", "default": code},
                                 "timeout_ms": {"type": "number", "default": 10000}}}}}],
            "transitions": transitions}


def controller_tool(name, code, description, params):
    """A tool the model calls to REPORT candidate values. The code is baked; the model only fills `params`.

    `params` maps a parameter name to a JSON-schema fragment (type, description, enum)."""
    props = {"code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 10000}}
    props.update(params)
    return {"type": "function", "config": {"timeoutMs": 10000},
            "function": {"name": name, "handler": "__function__:code_exec", "description": description,
                         "parameters": {"type": "object", "properties": props, "required": list(params)}}}


def close_node(name, api, outcome, reason, line, next_node="hang_up"):
    """Says a fixed line, closes the call in the bank's records (engine-run), then hangs up."""
    fields = {"outcome": outcome}
    if reason:
        fields["reason"] = reason
    return api_node(name, engine_call(api, "close_call", fields, retries=2), [], [always(next_node)], line=line)


def hang_up():
    return {"name": "hang_up", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
            "transitions": [],
            "terminal": {"type": "function", "function": {"name": "call_closed", "handler": "__function__:end_call",
                         "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}


def literal(obj):
    """Config as a Python literal for embedding in code. Only strings, numbers, lists and dicts; never `{{` or `}}`."""
    def walk(x):
        if x is None or isinstance(x, bool):
            raise ValueError("config for embedded code must not contain booleans or null")
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    text = json.dumps(obj, indent=1)
    if "{{" in text or "}}" in text:
        raise ValueError("config for embedded code contains a double brace")
    return text
