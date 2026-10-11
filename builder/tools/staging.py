"""Which practice customers are the basic ones. Pure function, no platform access."""


def smoke_ids(cases):
    """The basic customers: one per kind of call, the easiest kinds first, and one with several products. Chosen from what each customer is
    (family, level, products), never by id."""
    rank = {"easy": 0, "medium": 1, "hard": 2}
    picked, seen = [], set()
    for c in sorted(cases, key=lambda c: rank.get(c.get("level"), 3)):
        if c["family"] not in seen and len(picked) < 5:
            picked.append(c["id"])
            seen.add(c["family"])
    multi = [c["id"] for c in cases if len(c.get("products", [])) > 1]
    if multi and not set(multi) & set(picked):
        picked.append(multi[0])
    return [c["id"] for c in cases if c["id"] in picked]
