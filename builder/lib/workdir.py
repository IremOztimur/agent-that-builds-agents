"""The agent's clean working folder: only the inputs, the docs, one example agent, the helper tools and the skills.
The practice customers sit in a separate sealed folder; the agent reaches them only through tools/practice.py."""
import json, pathlib, shutil, tempfile

from . import intake
from .paths import BUILDER, KIT

SKILLS = ["read-brief", "compose-workflow", "test-and-repair"]


def prepare(brief, api, cases, dev=False):
    text = intake.brief_text(brief)
    intake.check_tool_api(api)
    work = pathlib.Path(tempfile.mkdtemp(prefix="builder-"))
    (work / "input").mkdir()
    bname = pathlib.Path(brief).name + (".txt" if pathlib.Path(brief).suffix.lower() == ".docx" else "")
    (work / "input" / bname).write_text(text)
    shutil.copy(api, work / "input" / pathlib.Path(api).name)
    (work / "inputs.json").write_text(json.dumps({"brief": "input/" + bname, "tools": "input/" + pathlib.Path(api).name,
                                                  "brief_lines": len(text.splitlines()), "cases": cases, "dev": dev}))
    (work / "topics.json").write_text(json.dumps(topics(cases), indent=1))
    (work / "docs").mkdir()
    for d in ("workflow-format.md", "tools-and-code.md", "api.md"):
        shutil.copy(KIT / "docs" / d, work / "docs" / d)
    (work / "examples").mkdir()
    shutil.copy(KIT / "examples" / "base-agent.json", work / "examples" / "base-agent.json")
    shutil.copy(KIT / "freya.py", work / "freya.py")
    shutil.copytree(BUILDER / "tools", work / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    for s in SKILLS:
        shutil.copytree(BUILDER / "skills" / s, work / ".claude" / "skills" / s)
    (work / "versions").mkdir()
    (work / ".sealed").write_text(str(_seal(work)))
    return work


def topics(cases):
    """What each practice customer does, never what the bank must show afterwards: no `expected`, no `checks`, no identity answers.
    The agent derives the expectations for each topic from the brief it is building for."""
    keep = ("id", "family", "level", "title", "script", "products", "faults")
    out = []
    for c in json.loads((KIT / "public-test-set.json").read_text()):
        if cases == "AB" or c["brief"] == cases:
            t = {k: c[k] for k in keep if k in c}
            t["products"] = [{"id": "p%d" % (i + 1), **p} for i, p in enumerate(c["products"])]     # the bank names them p1, p2, ... in this order
            out.append({**t, "now": c.get("variables", {}).get("now")})
    return out


def _seal(work):
    sealed = pathlib.Path(tempfile.mkdtemp(prefix="sealed-"))
    (sealed / "tools").mkdir()
    (sealed / "results").mkdir()
    for f in ("run_cases.py", "score.py"):
        shutil.copy(KIT / "tools" / f, sealed / "tools" / f)
    shutil.copy(KIT / "freya.py", sealed / "freya.py")
    shutil.copy(KIT / "public-test-set.json", sealed / "public-test-set.json")
    personas = BUILDER / ".personas.json"           # persona ids are reused so the workspace does not fill up
    if personas.exists():
        shutil.copy(personas, sealed / ".personas.json")
    else:
        (sealed / ".personas.json").write_text("{}")
    return sealed


def sealed_dir(work):
    return pathlib.Path((work / ".sealed").read_text())
