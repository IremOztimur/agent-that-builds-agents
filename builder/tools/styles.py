"""How each practice customer talks in a round. Pure function, no platform access.

Hidden customers talk like people, so a round gives every customer a fixed style from this cycle (None is plain talking). The assignment depends only
on the sorted ids and a shift: the same customers get the same styles in every round, so rounds stay comparable; the hold-out round shifts by one, so
every customer then talks differently.
"""
CYCLE = ["talkative", "pieces", "corrects", "asks_back", "in_words", None]


def assign(ids, shift=0):
    return {i: CYCLE[(n + shift) % len(CYCLE)] for n, i in enumerate(sorted(ids))}
