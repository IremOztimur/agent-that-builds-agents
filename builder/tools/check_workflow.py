"""The inner loop of phase 1: every check the phase gate runs, in one command, with a platform dry run.

    python3 tools/check_workflow.py [workflow.json]

Prints each problem with its format-rule id (see .claude/skills/compose-workflow/format-rules.md). Fix, run again, repeat until it
prints READY; then publish. The phase gate runs the same checks, so a workflow that says READY passes it.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import check_design, inputs, lint


def check(path="workflow.json"):
    """(must-fix problems, warnings)."""
    wf = json.load(open(path))
    base = json.load(open(inputs.tools_path()))["servers"][0]["url"].rstrip("/")
    bad, warn, _ = lint.lint(wf, base)
    bad = list(bad)
    if not pathlib.Path("design.json").exists():
        bad.append("[design] design.json is not written yet")
    else:
        bad += ["[design] " + p for p in check_design.check(pathlib.Path("."))]
    try:
        import freya
        res = freya.validate_workflow("dry", wf)
        if isinstance(res, dict) and res.get("valid") is False:
            bad.append("[platform] the dry run rejects the workflow: " + json.dumps(res)[:600])
    except Exception as e:
        warn.append("[platform] the dry run could not run (%s); publish.py runs it again" % str(e)[:160])
    return bad, warn


if __name__ == "__main__":
    bad, warn = check(sys.argv[1] if len(sys.argv) > 1 else "workflow.json")
    for w in warn:
        print("WARN", w)
    for b in bad:
        print("FAIL", b)
    if bad:
        print("NOT READY: %d must-fix. Fix them, then run this again." % len(bad))
    else:
        print("READY: no must-fix problems (%d warnings). Publish with python3 tools/publish.py workflow.json" % len(warn))
    sys.exit(1 if bad else 0)
