"""When to stop repairing, and which published version was best. Pure functions, no platform access; tools/practice.py applies them.

A round is a full run of every practice customer. A customer that failed but passes when rerun alone (`--only`) is noise, not a
failure. The stop rule exists to prevent overfitting: once the agent is strong and a repair did not reduce the failures, more repairs
would target single customers' wording instead of a rule of the brief.
"""
def is_dead(said_counts):
    """True when the platform answered nothing: in every call the agent said at most its opening line. A workflow does not do that to every customer."""
    return len(said_counts) >= 3 and all(n <= 1 for n in said_counts)


STRONG = 0.8        # share of customers that must pass for "already strong"
MAX_ROUNDS = 4


def full_rounds(rounds, all_ids):
    """Full rounds after noise reruns. `rounds` is a list of {"name", "only": ids or None, "failed": ids, "total": n, "pub": n}."""
    out = []
    for r in rounds:
        if r.get("style"):       # a run with another way of talking is not comparable with a full round
            continue
        only = set(r["only"]) if r.get("only") else None
        if only is None or only >= set(all_ids):
            out.append({"name": r.get("name"), "failed": set(r["failed"]), "total": r["total"], "pub": r.get("pub")})
        elif out:
            out[-1]["failed"] -= only - set(r["failed"])
    return out


def best(rounds, all_ids):
    """The full round with the most customers passing (the latest on a tie), or None."""
    full = full_rounds(rounds, all_ids)
    scored = [(f["total"] - len(f["failed"]), i, f) for i, f in enumerate(full) if f.get("pub") is not None]
    return max(scored, key=lambda t: (t[0], t[1]))[2] if scored else None


def verdict(rounds, all_ids):
    """None to continue, otherwise the reason to stop."""
    full = full_rounds(rounds, all_ids)
    if not full:
        return None
    last = full[-1]
    n, total = len(last["failed"]), last["total"]
    if n == 0:
        return "STOP: every practice customer passes. Nothing is left to repair."
    improved = lambda i: len(full[i]["failed"]) < len(full[i - 1]["failed"])
    if len(full) >= 2 and not improved(-1):
        if n <= (1 - STRONG) * total:
            stuck = sorted(last["failed"] & full[-2]["failed"])
            return ("STOP: the agent is already strong (%d of %d pass) and the last repair did not reduce the failures%s. Further repairs would "
                    "target single customers, not the brief. Finish with the best version." % (total - n, total, " (still failing: %s)" % ", ".join(stuck) if stuck else ""))
        if len(full) >= 3 and not improved(-2):
            return "STOP: two repairs in a row did not reduce the failures (%d of %d pass). Finish with the best version." % (total - n, total)
    if len(full) >= MAX_ROUNDS:
        return "STOP: %d rounds are used (%d of %d pass). Finish with the best version." % (len(full), total - n, total)
    return None


def needs_measuring(rounds, all_ids, pub):
    """True when the workflow published now is not the one the last full round measured. A repair that was never measured is wasted:
    the best measured version is what ships, so a changed workflow always gets one full round (the round cap still holds)."""
    full = full_rounds(rounds, all_ids)
    return bool(full) and full[-1].get("pub") != pub and len(full) < MAX_ROUNDS
