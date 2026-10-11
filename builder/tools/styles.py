"""How each practice customer talks in a round. Pure function, no platform access.

Hidden customers talk like people, so a round gives every customer a fixed style from this cycle (None is plain talking). The assignment depends only
on the sorted ids and a shift: the same customers get the same styles in every round, so rounds stay comparable; the hold-out round shifts by one, so
every customer then talks differently.
"""
CYCLE = ["talkative", "pieces", "corrects", "asks_back", "in_words", None]


def assign(ids, shift=0):
    return {i: CYCLE[(n + shift) % len(CYCLE)] for n, i in enumerate(sorted(ids))}


# How a customer talks. The facts of the case stay the same, only the way of saying them changes (the same texts as the kit's).
TEXT = {
    "pieces": "HOW YOU TALK: you give long numbers and dates in two parts. Say the first half, stop, and give the rest in your next turn or when asked. This replaces the rule about saying all of it in one turn.",
    "corrects": "HOW YOU TALK: the first time you say a day or an amount, you say a slightly different one first and correct yourself in the same sentence, like 'the 21st, sorry, I mean the 20th'. The corrected value is the one written above. Do this once or twice in the call, not more. Never do it with a security answer: those you say right the first time unless the text above says otherwise.",
    "talkative": "HOW YOU TALK: you talk a lot. Before most answers you add one or two sentences about your day, the traffic or how busy work is. Once in the call you mention that your cousin's wedding is on the 30th. It has nothing to do with any payment, and you never offer it as a payment day.",
    "asks_back": "HOW YOU TALK: twice in the call, before you answer, you ask a short question back, like 'why do you need that?' or 'which account is this about?'. Whatever the caller replies, you then give your answer.",
    "in_words": "HOW YOU TALK: you say every amount and every date in words and never in digits. Postcodes, years and other codes you say digit by digit.",
}
