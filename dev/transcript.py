"""Print the transcript and bank/tool events of runs saved by run_cases.py --out.

    source env.sh && python3 dev/transcript.py <results.json> [CASE ...]
"""
import json, pathlib, sys

KIT = pathlib.Path(__file__).resolve().parents[1] / "builder" / "kit"
sys.path.insert(0, str(KIT))
import freya

d = json.load(open(sys.argv[1]))
want = set(sys.argv[2:])
for r in d["rows"]:
    if want and r["id"] not in want:
        continue
    print("=" * 20, r["id"], "PASS" if r["pass"] else "FAIL", r["failed"][:1] and r["failed"][0][:200])
    call = freya.get_call(r["call_id"])
    print("ended:", call.get("endedReason"))
    for m in call["messages"]:
        if m["role"] in ("assistant", "user"):
            print(m["role"].upper()[:4], "|", m["message"][:300])
        else:
            try:
                ev = json.loads(m["message"])
            except Exception:
                continue
            if ev.get("event") == "function_call_start" and ev.get("function") in ("report_proposal", "report_confirmation", "report_answer", "api_call"):
                a = ev.get("args") or {}
                print("   >>", ev["function"], json.dumps(a.get("body", a.get("params", "")))[:160])
            elif ev.get("event") == "node_enter" and ev.get("node") in ("gate_promise", "close_refused", "close_service_error", "close_promise"):
                print("   >> node", ev["node"])
