"""Show why practice customers failed: the ledger diff, the judge's full reason, and the transcript with tool calls.

    python3 tools/show_failures.py results/r1.json [CASE ...]

Reads a file written by `tools/run_cases.py --out`. Without CASE it shows every failed customer. A line starting with
`>>` is a tool call the engine made (arguments shown), `node` lines show routing. The ledger lines come from the bank, not
from what the agent said.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya

d = json.load(open(sys.argv[1]))
want = set(sys.argv[2:])
print("%d / %d passed" % (d["passed"], d["total"]))
for r in d["rows"]:
    if (want and r["id"] not in want) or (not want and r["pass"]):
        continue
    print("=" * 18, r["id"], r.get("family", ""), "PASS" if r["pass"] else "FAIL")
    for f in r["failed"]:
        print("  -", f[:300])
    call = freya.get_call(r["call_id"])
    reason = (call.get("successCriteriaResult") or {}).get("reason")
    if reason:
        print("  JUDGE:", reason[:1200])
    print("  ended:", call.get("endedReason"), "| tools:", " > ".join(r.get("tools", [])))
    for m in call["messages"]:
        if m["role"] in ("assistant", "user"):
            print(" ", m["role"].upper()[:4], "|", m["message"][:260])
        else:
            try:
                ev = json.loads(m["message"])
            except Exception:
                continue
            e = ev.get("event")
            if e == "function_call_start":
                a = ev.get("args") or {}
                print("    >>", ev.get("function"), json.dumps(a.get("body", a.get("params", "")))[:200])
            elif e == "function_call_complete" and ev.get("function") in ("api_call",):
                print("    <<", json.dumps(ev.get("result", {}).get("data", ""))[:200])
            elif e == "node_enter":
                print("    node", ev.get("from_node"), "->", ev.get("node"))
            elif e == "error":
                print("    ERROR", json.dumps(ev)[:200])
