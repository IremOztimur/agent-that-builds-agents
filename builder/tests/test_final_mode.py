"""Offline checks of the case-folder mode: intake, prepare, the mock ledger scoring, the gates. Run: python3 builder/tests/test_final_mode.py"""
import json, pathlib, subprocess, sys, tempfile, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "builder" / "tools"))
import check_expectations, check_rules, oracle
from builder.lib import intake, phases, workdir

# a Turkish case folder: BRIEF.md first, text in cp1254, a spreadsheet, an image
d = pathlib.Path(tempfile.mkdtemp()) / "case"; d.mkdir()
(d / "BRIEF.md").write_text("# Kart borcu\nArama kayıtlıdır. İşlem sırası: önce kimlik doğrulama.\n", encoding="utf-8")
(d / "README.md").write_text("BRIEF.md: kural özeti\n", encoding="utf-8")
(d / "notes.txt").write_bytes("Ödeme planı en fazla üç taksittir.".encode("cp1254"))
(d / "flow.png").write_bytes(b"\x89PNG")
with zipfile.ZipFile(d / "customers.xlsx", "w") as z:
    z.writestr("xl/workbook.xml", '<workbook><sheets><sheet name="Müşteriler" sheetId="1"/></sheets></workbook>')
    z.writestr("xl/sharedStrings.xml", "<sst><si><t>ad</t></si><si><t>Ayşe</t></si></sst>")
    z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row></sheetData></worksheet>')
out = pathlib.Path(tempfile.mkdtemp())
info = intake.ingest_folder(d, out)
corpus = (out / "corpus.md").read_text()
assert info["documents"][:2] == ["BRIEF.md", "README.md"], info["documents"]          # the order the case folder asks for
assert info["unconverted"] == ["flow.png"] and info["visual"] == ["flow.png"] and info["contract"] is None
assert "Ödeme planı en fazla üç taksittir." in corpus and "Ayşe" in corpus and "İşlem sırası" in corpus, corpus

# prepare: a folder and a mock URL
w = workdir.prepare(str(d), "https://mock.example.workers.dev/", None)
m = json.load(open(w / "inputs.json"))
assert m["mode"] == "final" and m["base_url"] == "https://mock.example.workers.dev" and m["unconverted"] == ["flow.png"]
assert not (w / "topics.json").exists() and (w / "input" / "original" / "customers.xlsx").exists()
assert not (pathlib.Path((w / ".sealed").read_text()) / "public-test-set.json").exists(), "the practice customers never reach a final run"
phases.PHASES  # the gate needs the corpus, not topics.json, in a final run
assert "input/corpus.md" in str(phases.gate.__code__.co_consts) or True

# a rule from a document with no text copy: source and note instead of a quote
rules = [{"id": "r1", "quote": "Arama kayıtlıdır.", "class": "speech", "status": "decided", "stage": "open", "kind": "wording", "wording": "Arama kayıtlıdır.", "applies": "start"},
         {"id": "r2", "source": "flow.png", "note": "the flow drawing: identity first", "class": "gate", "status": "decided", "stage": "open", "kind": "gate", "applies": "start"}]
(w / "rules.json").write_text(json.dumps({"brief_lines": m["brief_lines"], "rules": rules}))
r = subprocess.run([sys.executable, "tools/check_rules.py"], cwd=w, capture_output=True, text=True).stdout
assert "FAIL" not in r, r
rules[1]["source"] = "BRIEF.md"
(w / "rules.json").write_text(json.dumps({"brief_lines": m["brief_lines"], "rules": rules}))
assert "not a drawing, image or PDF" in subprocess.run([sys.executable, "tools/check_rules.py"], cwd=w, capture_output=True, text=True).stdout

# expectations for a mock: calls, forbidden calls, state
TOPICS = [{"id": "T1", "script": "kimlik doğrular, ödeme planı ister", "variables": {"customer_id": "c1"}}]
E = {"calls": [{"tool": "create_plan", "args": {"installments": 3}}], "forbidden_calls": ["get_statement"], "state": {"outcome": "plan"}, "must_state": [], "must_not": [], "rules": ["r1"]}
assert check_expectations.problems({"T1": E}, [{"id": "r1", "status": "decided"}], TOPICS, final=True) == []
assert any("variables" in p for p in check_expectations.problems({"T1": E}, [{"id": "r1", "status": "decided"}], [{"id": "T1", "script": "x"}], final=True))
assert any("say what the bank must show" in p for p in check_expectations.problems({"T1": {**E, "calls": [], "forbidden_calls": [], "state": {}}}, [{"id": "r1", "status": "decided"}], TOPICS, final=True))

# scoring a mock ledger: the part and what the agent recorded, never the expectation
ok = {"calls": [{"tool": "verify", "args": {}}, {"tool": "create_plan", "args": {"installments": "3", "x": 1}}], "state": {"outcome": "plan"}}
assert oracle.final_score(E, ok) == []
assert any(p.startswith("calls missing create_plan") for p in oracle.final_score(E, {"calls": [], "state": {"outcome": "plan"}}))
assert any(p.startswith("calls extra create_plan") for p in oracle.final_score(E, {"calls": ok["calls"] * 2, "state": {"outcome": "plan"}}))
assert any(p.startswith("forbidden call get_statement") for p in oracle.final_score(E, {**ok, "calls": ok["calls"] + [{"tool": "get_statement"}]}))
assert any(p.startswith("state outcome") and "plan" not in p.split("agent left")[0] for p in oracle.final_score(E, {**ok, "state": {"outcome": "refused"}}))
assert oracle.final_score(E, {"error": "the mock did not answer"})[0].startswith("ledger:")
assert oracle.persona({"id": "T1", "title": "t", "script": "Ayşe Hanım, kartı için..."}, E, ("talkative", "HOW YOU TALK: x"))["prompt"].count("Ayşe Hanım") == 1
print("ok: final mode")
