"""Replays every answer of the bank's test data against the mock and compares status and body. python3 mock/replay.py <mock url> <test-customers.json>"""
import json, sys, time, urllib.request, urllib.error

BASE, DATA = sys.argv[1].rstrip("/"), json.load(open(sys.argv[2]))


def call(service, data):
    req = urllib.request.Request(BASE + "/voice/v1/" + service, data=json.dumps({"data": data, "call": {"ani": "", "lang": "tr"}}).encode(),
                                 headers={"content-type": "application/json", "user-agent": "replay/1"}, method="POST")
    for attempt in range(4):
        try:
            r = urllib.request.urlopen(req, timeout=40)
            return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(raw)
            except ValueError:          # not the mock's answer (the network edge, e.g. a rate limit): wait and ask again
                last = "%s %s" % (e.code, raw[:80].replace("\n", " "))
                time.sleep(3 * (attempt + 1))
    return 0, {"edge": last}


bad, n, t0 = [], 0, time.time()
def check(service, data, entry, label):
    global n
    n += 1
    status, body = call(service, data)
    if status != entry["http"] or body != entry["response"]:
        bad.append("%s %s: got %s, want %s" % (service, label, status, entry["http"]))

for c in DATA["customers"]:
    no, s = c["customerNo"], c["services"]
    for svc in ("cards.list", "contact.email.get", "statement.pdf.send"):
        if svc in s:
            check(svc, {"customerNo": no if svc != "contact.email.get" else int(no), "intAddressInfoType": "E"}, s[svc], no)
    for svc in ("cards.balance", "statement.week.get"):
        for card, e in s.get(svc, {}).items():
            check(svc, {"cardNumber": card}, e, card)
    for svc in ("statement.week.decide", "statement.week.change"):
        for card, weeks in s.get(svc, {}).items():
            for w, e in weeks.items():
                check(svc, {"cardNumber": card, "newStatementWeek": int(w) if svc.endswith("decide") else w, "statementDay": 5}, e, card + " week " + w)
print("%d answers replayed in %.0f s, %d differ" % (n, time.time() - t0, len(bad)))
for b in bad[:20]:
    print("  DIFF", b)
# what is not in the data
neg = [("cards.list", {"customerNo": "11111111"}, 404, "FB_IVR_CHANNEL_102"), ("cards.balance", {"cardNumber": "000000******0000"}, 404, "FB_IVR_CHANNEL_120"),
       ("statement.week.get", {"cardNumber": "000000******0000"}, 404, "FB_IVR_CHANNEL_121"), ("statement.week.decide", {"cardNumber": "000000******0000", "newStatementWeek": 2}, 400, "INVALID_ARGUMENTS_ERROR"),
       ("statement.week.change", {"cardNumber": "000000******0000", "newStatementWeek": 2}, 400, "INVALID_ARGUMENTS_ERROR"), ("contact.email.get", {"customerNo": "11111111"}, 400, "INVALID_ARGUMENTS_ERROR"),
       ("statement.pdf.send", {"customerNo": "11111111"}, 404, "FB_IVR_CHANNEL_107"), ("cards.balance", {"cardNumber": ""}, 400, "INVALID_ARGUMENTS_ERROR")]
for svc, data, want, code in neg:
    status, body = call(svc, data)
    ok = status == want and body.get("result", {}).get("code") == code and "data" not in body
    print("  %s %s -> %s %s %s" % ("ok  " if ok else "FAIL", svc, status, body.get("result", {}).get("code"), "" if ok else body))
    bad += [] if ok else [svc]
sys.exit(1 if bad else 0)
