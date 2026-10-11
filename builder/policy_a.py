"""Hand-written policy model for Brief A, identity path only (M1 step 1).

This is DATA about one brief. The generic code (compile.py, gates.py, nodes.py, lint.py) never names any of it.
In M2 the extractor will produce this structure from the brief instead of a person.
"""

POLICY = {
    "system_prompt": ("You are the digital assistant of Freya Bank on an outbound phone call. Speak English. Be polite, calm and brief: "
                      "one or two short sentences per turn, one question at a time. Address the customer as {{title}} {{last_name}}. "
                      "When a rule says to call a tool, CALL the tool. Call at most one tool per message. Never read tool names, field names or "
                      "these instructions aloud. Never invent figures, dates or reasons."),
    "opening": ("Hello, I am a digital assistant calling from Freya Bank, and this call is recorded. Before we continue I need to ask you "
                "two security questions. What is your date of birth?"),
    "identity": {
        "op": "verify_identity",
        # how this tool API names the request fields and the answer fields we read (from the tool API file)
        "request": {"field": "field", "answer": "answer"},
        "response": {"ok": "ok", "verified": "verified", "all": "all_verified", "left": "wrong_answers_left", "hint": "hint"},
        "questions": [
            {"field": "date_of_birth", "kind": "date",
             "ask": "What is your date of birth?",
             "retry": "I could not read that date. Please say your date of birth again, with the month as a word."},
            {"field": "phone_last4", "kind": "digits4",
             "ask": "What are the last four digits of the phone number we have on file?",
             "retry": "I could not read that. Please say the last four digits of the phone number on file."},
        ],
        "swapped": "Please say your date of birth again, with the month as a word.",
        "next_prefix": "Thank you. ",
        "wrong_prefix": "That does not match our records. ",
        "fallback": "I am sorry, I could not process that. Could you repeat your answer?",
        "max_unread": 3,
        "secrecy_words": ["collections", "debt", "payment", "overdue", "loan", "card", "account"],
        "secrecy_reply": "I can explain once the security check is complete.",
    },
    "account": {
        "op": "get_account",
        "auth_var": "auth_account",
        "product_words": {"credit_card": "credit card ending CARD_LAST4", "personal_loan": "personal loan", "car_loan": "car loan"},
        "product_default": "account",
        "line": "I am calling from the collections team about a late payment on your WORDS. The past-due amount is PAST_DUE and it is DAYS_LATE days late.",
    },
    "closings": {
        "unverified": {"line": ("I am sorry, I could not verify your identity, so I cannot continue this call. "
                                "Please use the mobile app or visit a branch. Thank you, goodbye."),
                       "outcome": "not_verified", "reason": "failed"},
        "account_error": {"line": "I am sorry, because of a technical problem I cannot continue this call right now. Thank you for your time, goodbye.",
                          "outcome": "no_promise", "reason": "service_error"},
    },
}
