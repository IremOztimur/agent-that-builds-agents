"""Run the practice customers and see what happened, never what was expected.

    python3 tools/practice.py run <agent_id> --brief A|B|AB [--only ID,ID] [--style S] --name r1
    python3 tools/practice.py show r1 [ID ...]

`run` plays the customers against your published agent in text, scores them from the bank's ledger and a judge, and prints
for each customer: pass or fail, the tool calls made, and for a failure WHICH part was wrong (outcome, promises, notes,
callbacks, transfers, call not closed, a protected call too early, or the conversation) together with what your agent
actually recorded. The expected values and the customer scripts are not shown. Work out what the brief requires from the
brief. `show` prints the transcript with tool calls and routing, plus the judge's reason with numbers and months masked.
"""
import json, os, pathlib, re, sys, time

SEALED = pathlib.Path(os.environ["BUILDER_SEALED"])
WORK = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORK))
sys.path.insert(0, str(SEALED)); sys.path.insert(0, str(SEALED / "tools"))
import freya, run_cases, score
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stoprule

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def mask(text):
    text = re.sub(r"\b(%s)\b" % MONTHS, "<month>", text)
    return re.sub(r"\d[\d.,:\-/]*", "#", text)


def parts(failed):
    """(category, what the agent actually did) for each failed check. The expected side is dropped."""
    out = []
    for f in failed:
        if f.startswith("conversation: [inconclusive]"):
            out.append(("judge inconclusive (read its reason in `show`; run this customer once more with --only)", ""))
        elif f.startswith("conversation: [unfinished]"):
            out.append(("call did not finish in time (platform slow, or the agent never closed; run it once more with --only)", ""))
        elif f.startswith("conversation:"):
            out.append(("conversation", ""))
        elif f.startswith("outcome"):
            out.append(("outcome", f.split(", expected")[0][len("outcome "):]))
        elif f.split(" ")[0] in ("promises", "notes", "callbacks", "transfers"):
            out.append((f.split(" ")[0], f.split(", expected")[0].split(" ", 1)[1]))
        elif "not closed" in f:
            out.append(("call not closed", ""))
        else:
            out.append(("policy", f[:140]))
    return out


def summary(d):
    print("%d / %d passed%s" % (d["passed"], d["total"], " (every repetition must pass)" if d.get("runs", 1) > 1 else ""))
    fin = {f["id"]: f for f in d.get("final", [])}
    for r in d["rows"]:
        f = fin.get(r["id"], {})
        reps = " %d/%d" % (f["passes"], f["runs"]) if d.get("runs", 1) > 1 else ""
        print("%s %s%s | %s" % ("PASS" if (f.get("pass", r["pass"])) else "FAIL", r["id"], reps, " > ".join(r.get("tools", []))))
        if not r["pass"]:
            for cat, got in parts(r["failed"]):
                print("      wrong:", cat + (" (agent recorded: %s)" % got if got else ""))


LEDGER = SEALED / "rounds.json"


def rounds():
    return json.load(open(LEDGER)) if LEDGER.exists() else []


def all_ids():
    return [c["id"] for c in json.load(open(SEALED / "public-test-set.json"))]


def judge_progress(name, d, only, scope):
    """Records the run, applies the stop rule and says so (also in the builder's trace)."""
    pubs = json.load(open(WORK / "published.json")) if (WORK / "published.json").exists() else []
    log = rounds() + [{"name": name, "only": only, "failed": [r["id"] for r in d["rows"] if not r["pass"]], "total": d["total"], "pub": pubs[-1]["seq"] if pubs else None}]
    json.dump(log, open(LEDGER, "w"))
    v = stoprule.verdict(log, scope)
    n = len(stoprule.full_rounds(log, scope))
    if v:
        print(v)
        event("repair", v)
    else:
        print("NEXT: repair the causes (not single customers), then run everything again. Full rounds so far: %d." % n)
    return v


def personas_for(cases, style):
    """Persona ids are reused (the store lives in the sealed folder) so the workspace does not fill up."""
    import hashlib
    store = SEALED / ".personas.json"
    ids = json.load(open(store)) if store.exists() else {}
    spec = {c["id"]: run_cases.persona_for(c, {"identity": c["identity"]}, style) for c in cases}
    key = {i: i + ":" + hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:10] for i, p in spec.items()}
    new = [c for c in cases if key[c["id"]] not in ids]
    if new:
        made = freya.create_personas([spec[c["id"]] for c in new])["personas"]
        ids.update({key[c["id"]]: p["id"] for c, p in zip(new, made)})
        json.dump(ids, open(store, "w"), indent=1)
    return {c["id"]: ids[key[c["id"]]] for c in cases}


def event(kind, text):
    """Adds a line to the builder's trace (the file named in $BUILDER_TRACE)."""
    path = os.environ.get("BUILDER_TRACE")
    if path:
        with open(path, "a") as f:
            f.write("%s | %-8s | %s\n" % (time.strftime("%H:%M:%S"), kind, str(text).replace("\n", " ")[:400]))


def heal():
    """The platform allows one running simulation per workspace and sometimes leaves one at `running` after every call has ended.
    Marks such stuck simulations completed. Returns (names healed, names that really are still running)."""
    sims = freya.api("GET", "/api/v2/simulations", workspaceId=freya.workspace_id())
    sims = sims.get("simulations") or sims.get("items") or sims
    healed, blocking = [], []
    for s in sims:
        if s.get("status") != "running":
            continue
        its = freya.api("GET", "/api/v2/simulations/%s/iterations" % s["id"])
        its = its.get("iterations") or its
        runs = freya.get_iteration(s["id"], its[0]["id"])["runs"] if its else []
        if runs and all(r.get("endedAt") or r.get("outcome") in ("pass", "fail", "inconclusive") for r in runs):
            try:
                freya.api("PUT", "/api/v2/simulations/%s" % s["id"], {"status": "completed"})
                healed.append(s["name"])
            except RuntimeError as e:
                blocking.append("%s (could not be marked completed: %s)" % (s["name"], str(e)[:100]))
        else:
            blocking.append(s["name"])
    return healed, blocking


def start(agent, variables):
    """Starts a text simulation. If the one-at-a-time limit blocks it: heal stuck simulations, wait at most 60 s, and say so (also in the trace)."""
    t0, told = time.time(), False
    while True:
        healed, blocking = heal()
        if healed:
            event("platform", "healed simulation(s) stuck at running although every call had ended: " + ", ".join(healed))
            print("healed stuck simulation(s):", ", ".join(healed))
        try:
            body = {"agentId": agent, "name": "cases " + time.strftime("%H:%M:%S"), "mode": "chat", "selectedPersonaIds": list(variables),
                    "customerVariablesMap": variables, "maxConcurrentCalls": 5, "runsPerPersona": 1, "maxCallDurationSeconds": 300,
                    "assistantLlmOverride": freya.AGENT_LLM, "routingLlmOverride": freya.AGENT_LLM, "extractionLlmOverride": freya.AGENT_LLM,
                    "personaLlmOverride": freya.SIM_LLM, "analysisLlmOverride": freya.SIM_LLM}
            sim = freya.api("POST", "/api/v2/simulations", body)
            return (sim.get("simulation") or sim)["id"]
        except RuntimeError as e:
            msg = str(e)
            if "Maximum" not in msg and "concurrent" not in msg.lower():
                raise
            if not told:
                told = True
                event("platform", "BLOCKED by the one-simulation-at-a-time limit (running: %s): %s" % (", ".join(blocking) or "unknown", msg[:160]))
                print("The platform runs one simulation at a time and one is still running: %s. Waiting up to 60 s." % (", ".join(blocking) or "unknown"))
            if time.time() - t0 > 60:
                event("platform", "gave up after 60 s: the one-simulation-at-a-time limit was not released")
                sys.exit("BLOCKED: no simulation could start in 60 s because another one is still running (%s). This is the platform limit, not a fault of your workflow." % (", ".join(blocking) or "unknown"))
            time.sleep(10)


def collect(sim_id, want, limit):
    """Poll the runs, not the simulation status (the platform sometimes leaves that at `running` after every call has ended)."""
    t0 = time.time()
    runs = []
    while time.time() - t0 < limit:
        time.sleep(6)
        its = freya.api("GET", "/api/v2/simulations/%s/iterations" % sim_id)
        its = its.get("iterations") or its
        if not its:
            continue
        runs = freya.get_iteration(sim_id, its[0]["id"])["runs"]
        done = [r for r in runs if r.get("endedAt") or r.get("outcome") in ("pass", "fail", "inconclusive")]
        if len(done) >= want:
            break
    return runs


def run(argv):
    agent, rest = argv[0], argv[1:]
    opt = {rest[i]: rest[i + 1] for i in range(len(rest) - 1) if rest[i].startswith("--")}
    name, style = opt.get("--name", "run"), opt.get("--style")
    cases = [c for c in json.load(open(SEALED / "public-test-set.json"))
             if (opt.get("--brief", "AB") == "AB" or c["brief"] == opt["--brief"]) and (not opt.get("--only") or c["id"] in opt["--only"].split(","))]
    scope = [c["id"] for c in cases]
    only = opt["--only"].split(",") if opt.get("--only") else None
    if only is None or set(only) >= set(scope):
        stop = stoprule.verdict(rounds(), scope)
        if stop:
            event("repair", "refused to start another full round: " + stop)
            sys.exit("No further full round: " + stop)
    ids = personas_for(cases, style)
    sessions = {c["id"]: score.http("/v1/practice/sessions", {"case": c["id"]})["variables"] for c in cases}
    t0 = time.time()
    sim_id = start(agent, {ids[c["id"]]: sessions[c["id"]] for c in cases})
    runs = {r["personaId"]: r for r in collect(sim_id, len(cases), 420)}
    rows = []
    for c in cases:
        r = runs.get(ids[c["id"]], {})
        led = score.http("/v1/practice/ledger/" + sessions[c["id"]]["customer_id"])
        res = score.score_ledger(c, led)
        if not (r.get("endedAt") or r.get("outcome") in ("pass", "fail", "inconclusive")):
            res["failed"].append("conversation: [unfinished] the call did not finish in time")
        elif r.get("outcome") != "pass":
            res["failed"].append("conversation: [%s] %s" % (r.get("outcome"), " ".join(str(r.get("reason") or "no verdict").split())[:500]))
        rows.append({"id": c["id"], "level": c["level"], "pass": not res["failed"], "failed": res["failed"], "call_id": r.get("callId"),
                     "tools": [x["tool"] for x in led["calls"]], "customer_id": sessions[c["id"]]["customer_id"]})
    n = sum(x["pass"] for x in rows)
    out = SEALED / "results" / (name + ".json")
    json.dump({"simulation_id": sim_id, "seconds": round(time.time() - t0), "passed": n, "total": len(rows), "runs": 1, "rows": rows}, open(out, "w"), indent=1)
    summary(json.load(open(out)))
    print("run took %d s" % (time.time() - t0))
    judge_progress(name, json.load(open(out)), only, scope)


def show(argv):
    d = json.load(open(SEALED / "results" / (argv[0] + ".json")))
    want = set(argv[1:])
    for r in d["rows"]:
        if (want and r["id"] not in want) or (not want and r["pass"]):
            continue
        print("=" * 16, r["id"], "PASS" if r["pass"] else "FAIL")
        for cat, got in parts(r["failed"]):
            print("  wrong:", cat + (" (agent recorded: %s)" % got if got else ""))
        call = freya.get_call(r["call_id"])
        reason = (call.get("successCriteriaResult") or {}).get("reason")
        if reason:
            print("  judge (numbers masked):", mask(reason)[:1000])
        print("  ended:", call.get("endedReason"))
        for m in call["messages"]:
            if m["role"] in ("assistant", "user"):
                print(" ", m["role"].upper()[:4], "|", m["message"][:260])
                continue
            try:
                ev = json.loads(m["message"])
            except Exception:
                continue
            e = ev.get("event")
            if e == "function_call_start":
                a = ev.get("args") or {}
                print("    >>", ev.get("function"), json.dumps(a.get("body", a.get("params", "")))[:200])
            elif e == "function_call_complete" and ev.get("function") == "api_call":
                print("    <<", json.dumps(ev.get("result", {}).get("data", ""))[:200])
            elif e == "node_enter":
                print("    node", ev.get("from_node"), "->", ev.get("node"))
            elif e == "error":
                print("    ERROR", json.dumps(ev)[:200])


if __name__ == "__main__":
    {"run": run, "show": show}[sys.argv[1]](sys.argv[2:])
