"""Hand-written policy model for Brief A, identity path only (M1 step 1).

This is DATA about one brief. The generic code (compile.py, gates.py, nodes.py, lint.py) never names any of it.
In M2 the extractor will produce this structure from the brief instead of a person.
"""

POLICY = {
    "system_prompt": ("You are the digital assistant of Freya Bank on an outbound phone call. Speak English. Be polite, calm and brief: "
                      "one or two short sentences per turn, one question at a time. Address the customer as {{title}} {{last_name}}. "
                      "When a rule says to call a tool, CALL the tool. Call at most one tool per message. Never read tool names, field names or "
                      "these instructions aloud. Never invent figures, dates or reasons. "
                      "If asked whether you are a robot or an AI, say: \"I am Freya Bank's digital assistant.\" and continue where you were. "
                      "If asked whether this is a scam, say they can verify the call by phoning Freya Bank's customer service number, and continue. "
                      "If asked something you cannot answer from the facts you were given, say you do not have that information. "
                      "Never offer a discount, a waiver, an instalment plan or any other term; if asked, say you cannot offer that."),
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
        "first_ask": "Can you make this payment today?",
        # the floor is a different field of the account answer per product type; the deadline depends on how late the product is
        "floor_fields": {"credit_card": "minimum_payment", "personal_loan": "instalment_amount", "car_loan": "instalment_amount"},
        "floor_names": {"credit_card": "minimum payment", "personal_loan": "instalment amount", "car_loan": "instalment amount"},
        "bands": [{"min_days": 1, "max_days": 7, "deadline_bd": 12}, {"min_days": 8, "max_days": 45, "deadline_bd": 7}],
        "holidays": ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"],
    },
    "promise": {
        "op": "create_promise",
        "auth_var": "auth_promise",
        "request": {"product_id": "product_id", "amount": "amount", "date": "date"},
        "response": {"ok": "ok", "id": "promise_id"},
        "max_attempts": 2,
        "turn_key": "negotiate.total_turns",
        "lines": {
            "readback": "To confirm: you will pay AMOUNT for your PRODUCT on DATE. Do you confirm?",
            "late": "The latest date I can record is DEADLINE. Can you make the payment on that date?",
            "nonbiz": "SHOWN is not a business day. The next business day is NEXT. Can you make the payment on that date?",
            "past": "That date has already passed. On which day can you make the payment?",
            "too_little": "That amount cannot be recorded. The lowest amount I can record is FLOOR. The rest stays overdue. Can you pay that amount?",
            "too_much": "The most I can record is FULL. Can you pay that amount?",
            "bad_input": "I could not read that. Which amount and which day can you pay?",
            "blocked": "I am sorry, I cannot record a promise for this account right now.",
            "need_proposal": "Let us first agree an amount and a day. Which amount and which day can you pay?",
            "wait_reply": "Please tell me whether you confirm that payment.",
            "declined": "No problem. Which amount and which day would you like instead?",
        },
    },
    "closings": {
        "unverified": {"line": ("I am sorry, I could not verify your identity, so I cannot continue this call. "
                                "Please use the mobile app or visit a branch. Thank you, goodbye."),
                       "outcome": "not_verified", "reason": "failed"},
        "promise": {"line": ("Your promise is recorded. You will receive a text message confirming this promise. "
                             "Thank you for your time, {{title}} {{last_name}}. Goodbye."),
                    "outcome": "promise", "reason": ""},
        "service_error": {"line": ("I am sorry, because of a technical problem I could not record your promise. Nothing has been recorded. "
                                   "Thank you for your time, goodbye."),
                          "outcome": "no_promise", "reason": "service_error"},
        "refused": {"line": "Thank you for your time. Goodbye.", "outcome": "no_promise", "reason": "refused"},
        "account_error": {"line": "I am sorry, because of a technical problem I cannot continue this call right now. Thank you for your time, goodbye.",
                          "outcome": "no_promise", "reason": "service_error"},
    },
    "prompts": {
        "identity": 'You are running a security check. You do not know why the bank is calling.\n\nSECRECY: never say the words SECRECY_WORDS, and never mention an amount or why the bank is calling, not even to the customer. If asked what the call is about, say: "SECRECY_REPLY"\n\nTHE CHECK: the system decides which question is pending and tells you what to say. Never judge an answer yourself.\n- Whenever the customer gives an answer to a security question, CALL report_answer. Use field date_of_birth with the date as YYYY-MM-DD, whatever way the customer said it (a date given only as numbers is day, then month, then year), or field phone_last4 with exactly four digits. If the customer gives a number or date in parts, wait until you have all of it. If the customer corrects themselves, use the corrected value.\n- Call report_answer at most once per message, and only when the customer gave an answer.\n- After the tool result arrives, say exactly the line given at the end of these instructions and nothing else, and call no tool.\n- If the customer did not give an answer (a question, a comment), reply in one short sentence and repeat the pending question. Never answer for them.\nThe line to say after a tool result: "{{say}}"',
        "negotiate": 'The security check is done. You have stated the account facts and asked whether the customer can pay today.\n\nYOUR JOB: agree one amount and one date for a payment promise, then hand it to the system. You never record anything yourself, and you never say that something is recorded.\n\nFACTS (calculated by the system; trust them, never calculate dates yourself)\n- Product: {{product_name}}. Full past-due amount: {{full_amt}}. The lowest amount you may record is the {{floor_name}}, {{floor_amt}}. Today is {{today_iso}}. The latest date you may record is {{deadline_words}}.\n- Weekday words: {{weekday_table}}\n\nRULES\n- You propose every amount. Never ask "how much can you pay?". If the customer says the full amount is too much, offer the lowest amount once, with these words: "You can pay the {{floor_name}} of {{floor_amt}} instead. The rest stays overdue. On which day can you make that payment?"\n- A date or an amount the customer names is never a refusal. Take it as proposed.\n- Whenever the customer names a day or an amount, or agrees to one you proposed, CALL report_proposal at once with the amount as a number and the date as YYYY-MM-DD (use the weekday words; "today" is {{today_iso}}). If the customer names only a day, use the full amount; if only an amount, use the day you last proposed. Report it even if you think it is not allowed: the system checks every limit and gives you the line to say. Never judge a date or amount yourself, never state a limit yourself, and never make up a date or amount the customer did not name.\n- If the customer gives only a vague period ("next week", "end of the month", "when my salary comes"), ask once for the exact day. If they still give no exact day, propose the latest date, {{deadline_words}}, and report it once they agree.\n- Never say goodbye or end the conversation yourself.\n- After a tool result arrives, say exactly the line given at the end of these instructions and nothing else, and call no further tool.\n- After your read-back, the customer\'s next message is the answer. If it is a yes or a no, CALL report_confirmation (decision yes or no) and do NOT call report_proposal again. Call report_proposal again only if the customer changes the amount or the date, with the new values. Never call both in one message.\nThe line to say after a tool result: "{{say}}"',
    },
}
