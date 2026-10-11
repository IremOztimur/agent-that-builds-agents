"""When to stop repairing. Pure functions, no platform access; tools/practice.py applies them and refuses to start another full round.

A round is a full run of every practice customer. A customer that failed but passes when rerun alone (`--only`) is noise, not a
failure. The rule exists to prevent overfitting: once the agent is strong and a failure survives a repair, more repairs would target
that one customer's wording instead of a rule of the brief.
"""
STRONG = 0.8        # share of customers that must pass for "already strong"
MAX_ROUNDS = 4


def full_rounds(rounds, all_ids):
    """Failing sets of the full rounds after noise reruns. `rounds` is a list of {"only": ids or None, "failed": ids, "total": n}."""
    out = []
    for r in rounds:
        only = set(r["only"]) if r.get("only") else None
        if only is None or only >= set(all_ids):
            out.append({"failed": set(r["failed"]), "total": r["total"]})
        elif out:
            out[-1]["failed"] -= only - set(r["failed"])
    return out


def verdict(rounds, all_ids):
    """None to continue, otherwise the reason to stop."""
    full = full_rounds(rounds, all_ids)
    if not full:
        return None
    last = full[-1]
    n, total = len(last["failed"]), last["total"]
    if n == 0:
        return "STOP: every practice customer passes. Nothing is left to repair."
    strong = n <= (1 - STRONG) * total
    if len(full) >= 2 and last["failed"] == full[-2]["failed"]:
        if strong:
            return ("STOP: the agent is already strong (%d of %d pass) and the last repair changed nothing: the same failures remain (%s). "
                    "Further repairs would target single customers, not the brief. Finish with the best version." % (total - n, total, ", ".join(sorted(last["failed"]))))
        if len(full) >= 3 and full[-3]["failed"] == last["failed"]:
            return "STOP: the same %d failures survived two repairs (%s). Finish with the best version." % (n, ", ".join(sorted(last["failed"])))
    if len(full) >= MAX_ROUNDS:
        return "STOP: %d rounds are used (%d of %d pass). Finish with the best version." % (len(full), total - n, total)
    return None
