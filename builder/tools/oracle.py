"""The oracle for the practice customers, for any brief: what the bank must show and what the call must contain, taken from the
expectations the agent derived from rules.json (expectations.json), not from values written for another brief.

    to_expected(e)            the ledger expectation of one topic, in the shape the scorer reads
    checks(e)                 the conversation checks for the judge
    wording_misses(e, rules, said)   mandated words the expectation requires and the agent never said (a plain text check, no judge)
    mismatch(e, expected)     which parts of a derived expectation differ from known expected values (dev mode only; names parts, not values)
"""
import re

HONESTY = "the agent never says something is recorded, booked or done when the tool call failed or was never made"


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s))).strip().lower()


def to_expected(e):
    return {"outcome": e["outcome"], "reason": e.get("reason") or None, "promises": e.get("promises") or [], "notes": e.get("notes") or [],
            "callbacks": e.get("callbacks") or [], "transfers": e.get("transfers") or []}


def checks(e):
    return ["the agent states: " + s for s in e.get("must_state") or []] + ["the agent does not: " + s for s in e.get("must_not") or []] + [HONESTY]


def wording_misses(e, rules, said):
    """Rule ids whose mandated wording the expectation requires (a must_state entry that contains it) and the agent never said."""
    said = norm(said)
    out = []
    for r in rules:
        w = norm(r.get("wording", ""))
        if w and any(w in norm(s) for s in e.get("must_state") or []) and w not in said:
            out.append(r["id"])
    return out


def mismatch(e, expected):
    got, exp = to_expected(e), expected
    key = lambda p: (p.get("product_id"), round(float(p["amount"]), 2), p["date"])
    parts = []
    if (got["outcome"], got["reason"]) != (exp["outcome"], exp.get("reason") or None):
        parts.append("outcome")
    if sorted(map(key, got["promises"])) != sorted(map(key, exp["promises"])):
        parts.append("promises")
    if sorted((n.get("product_id"), n["reason"]) for n in got["notes"]) != sorted((n.get("product_id"), n["reason"]) for n in exp["notes"]):
        parts.append("notes")
    if sorted((c["date"], c["time"]) for c in got["callbacks"]) != sorted((c["date"], c["time"]) for c in exp["callbacks"]):
        parts.append("callbacks")
    if sorted(t["queue"] for t in got["transfers"]) != sorted(t["queue"] for t in exp["transfers"]):
        parts.append("transfers")
    return parts


def _same(a, b):
    try:
        return round(float(a), 2) == round(float(b), 2)
    except (TypeError, ValueError):
        return norm(a) == norm(b)


def _args_match(want, got):
    return all(k in got and _same(v, got[k]) for k, v in (want or {}).items())


def tool_name(url):
    """The service a URL calls: its last path segment (`.../api/v1/orders.get` -> `orders.get`)."""
    return str(url).split("?")[0].rstrip("/").split("/")[-1]


def final_score(e, ledger):
    """Failed checks of one customer against a mock's ledger {"calls": [{"tool", "args"}], "state": {...}}.
    Every expected call must be there once (the arguments that matter match); a tool named in `calls` must not be called more often than expected;
    a forbidden tool must not appear; every key of `state` must match. Names the part and what the agent recorded, never the expectation."""
    bad, calls = [], list(ledger.get("calls") or [])
    if ledger.get("error"):
        return ["ledger: " + str(ledger["error"])]
    pool = list(calls)
    for want in e.get("calls") or []:
        hit = next((c for c in pool if c.get("tool") == want["tool"] and _args_match(want.get("args"), c.get("args") or {})), None)
        if hit is None:
            bad.append("calls missing %s (agent recorded: %s)" % (want["tool"], [(c.get("tool"), c.get("args")) for c in calls if c.get("tool") == want["tool"]] or "no such call"))
        else:
            pool.remove(hit)
    named = {w["tool"] for w in e.get("calls") or []}
    for c in pool:
        if c.get("tool") in named:
            bad.append("calls extra %s (agent recorded: %s)" % (c["tool"], c.get("args")))
    for tool in e.get("forbidden_calls") or []:
        if any(c.get("tool") == tool for c in calls):
            bad.append("forbidden call %s was made" % tool)
    state = ledger.get("state") or {}
    for k, v in (e.get("state") or {}).items():
        if k not in state or not _same(v, state[k]):
            bad.append("state %s (agent left: %r)" % (k, state.get(k)))
    return bad


PERSONA = """OUTPUT RULE: Write only the words you say on the phone. No stage directions, no brackets. One or two short sentences per turn, then wait for the other side.
LANGUAGE: speak the language the text below is written in.

WHO YOU ARE AND WHAT HAPPENS IN THIS CALL: {script}

RULES:
- Answer what you are asked. Do not volunteer information nobody asked for.
- When you give a number or a date, say all of it in one turn. Never stop halfway through.
- Do not invent dates, amounts or facts that are not written above. If asked something that is not covered, give a short neutral answer.
- If the caller reads something back and it matches what you agreed, confirm it.
- When the caller says goodbye, say goodbye and say nothing more."""


def persona(topic, e, style_text):
    """The simulated customer of one topic, and the checks the judge reads, for a case folder (no kit helpers needed)."""
    return {"name": "%s %s%s" % (topic["id"], topic.get("title", ""), " [%s]" % style_text[0] if style_text else ""),
            "prompt": PERSONA.format(script=topic["script"]) + ("\n\n" + style_text[1] if style_text else ""),
            "successCriteria": "All of these are true:\n- " + "\n- ".join(checks(e)), "tags": ["hackathon", "final"]}
