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
