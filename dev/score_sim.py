"""Score a finished simulation without waiting for its status flag (the platform sometimes leaves it at `running`).

    source env.sh && python3 dev/score_sim.py [simulation_id] [--out file.json]

Reads every run of the simulation, finds the customer id in the call's variable table, scores the bank ledger with the
kit's scorer and takes the judge's verdict from the run (`inconclusive` counts as a failure, like any non-pass).
Defaults to the newest simulation.
"""
import json, pathlib, sys

KIT = pathlib.Path(__file__).resolve().parents[1] / "builder" / "kit"
sys.path.insert(0, str(KIT)); sys.path.insert(0, str(KIT / "tools"))
import freya
from score import http, score_ledger

cases = {c["id"]: c for c in json.load(open(KIT / "public-test-set.json"))}
argv = sys.argv[1:]
out = argv[argv.index("--out") + 1] if "--out" in argv else None
args = [a for a in argv if not a.startswith("--") and a != out]
sims = freya.api("GET", "/api/v2/simulations", workspaceId=freya.workspace_id())
sims = sims.get("simulations") or sims.get("items") or sims
sim = next((s for s in sims if s["id"] == args[0]), None) if args else sims[0]
its = freya.api("GET", "/api/v2/simulations/%s/iterations" % sim["id"]); its = its.get("iterations") or its
runs = freya.get_iteration(sim["id"], its[0]["id"])["runs"]
rows = []
for r in sorted(runs, key=lambda r: r["personaName"]):
    cid = r["personaName"].split()[0]
    call = freya.get_call(r["callId"])
    cust = None
    for m in call["messages"]:
        if m["role"] == "system":
            try:
                ev = json.loads(m["message"])
            except Exception:
                continue
            vt = ev.get("variable_table") or {}
            v = vt.get("customer_id")
            cust = (v.get("value") if isinstance(v, dict) else v) or cust
    led = http("/v1/practice/ledger/" + cust)
    res = score_ledger(cases[cid], led)
    if r["outcome"] != "pass":
        res["failed"].append("conversation: [%s] %s" % (r["outcome"], " ".join(str(r.get("reason") or "no verdict").split())[:500]))
    rows.append({"id": cid, "level": cases[cid]["level"], "pass": not res["failed"], "failed": res["failed"], "call_id": r["callId"], "customer_id": cust,
                 "tools": [x["tool"] for x in led["calls"]], "ended": call.get("endedReason"), "duration": call.get("duration")})
    print("PASS" if not res["failed"] else "FAIL", cid, cases[cid]["level"], "|", " > ".join(t.replace("verify_identity", "verify").replace("create_promise", "promise") for t in rows[-1]["tools"]), "| %ss" % call.get("duration"))
    for f in res["failed"]:
        print("       -", f[:280])
n = sum(x["pass"] for x in rows)
print("\n%d / %d passed (one repetition)" % (n, len(rows)))
if out:
    json.dump({"simulation_id": sim["id"], "passed": n, "total": len(rows), "rows": rows}, open(out, "w"), indent=1)
