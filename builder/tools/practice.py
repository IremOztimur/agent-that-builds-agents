"""Run the practice customers and see what happened, never what was expected.

    python3 tools/practice.py run <agent_id> --brief A|B [--only ID,ID] [--reps N] [--style S] --name r1
    python3 tools/practice.py show r1 [ID ...]

`run` plays the customers against your published agent in text, scores them from the bank's ledger and a judge, and prints
for each customer: pass or fail, the tool calls made, and for a failure WHICH part was wrong (outcome, promises, notes,
callbacks, transfers, call not closed, a protected call too early, or the conversation) together with what your agent
actually recorded. The expected values and the customer scripts are not shown. Work out what the brief requires from the
brief. `show` prints the transcript with tool calls and routing, plus the judge's reason with numbers and months masked.
"""
import json, os, pathlib, re, subprocess, sys

SEALED = pathlib.Path(os.environ["BUILDER_SEALED"])
WORK = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORK))
import freya

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def mask(text):
    text = re.sub(r"\b(%s)\b" % MONTHS, "<month>", text)
    return re.sub(r"\d[\d.,:\-/]*", "#", text)


def parts(failed):
    """(category, what the agent actually did) for each failed check. The expected side is dropped."""
    out = []
    for f in failed:
        if f.startswith("conversation:"):
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


def run(argv):
    agent, rest = argv[0], argv[1:]
    name = "run"
    if "--name" in rest:
        i = rest.index("--name")
        name = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
    out = SEALED / "results" / (name + ".json")
    p = subprocess.run([sys.executable, str(SEALED / "tools" / "run_cases.py"), agent] + rest + ["--out", str(out)], capture_output=True, text=True, cwd=str(SEALED))
    if not out.exists():
        print((p.stdout + p.stderr)[-1500:])
        sys.exit("run failed")
    d = json.load(open(out))
    summary(d)
    tail = [l for l in p.stdout.splitlines() if l.startswith(("slowest agent turn", "WARNING"))]
    print("\n".join(tail))


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
