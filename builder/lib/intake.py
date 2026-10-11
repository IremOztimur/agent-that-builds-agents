"""Reads the inputs, whatever they are called, and fails loudly when one cannot be used.
A single brief file plus a tool API file (development), or a case folder of documents (the final): Markdown, text, Word, Excel, PDF, images."""
import json, pathlib, re, sys, zipfile

TEXT = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html", ".htm", ".xml", ".tsv", ".js", ".ts", ".py", ".toml", ".ini", ".sql"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
DATA = {".json", ".csv", ".tsv", ".xml"}
BIG = 40_000            # a data file above this many bytes is listed, not inlined: nobody reads 700 KB of records line by line
FIRST = ["brief.md", "readme.md"]          # the case folder says: read BRIEF.md first, README.md says what each document is


def brief_text(path):
    """The brief as text. A specification, mail, memo, notes or transcript; .docx is unpacked."""
    p = pathlib.Path(path)
    if not p.is_file():
        sys.exit("brief not found: %s" % path)
    if p.suffix.lower() == ".docx":
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", "ignore")
        text = re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n"))
    else:
        try:
            text = p.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            sys.exit("the brief %s is not UTF-8 text; convert it to text first" % path)
    if not text.strip():
        sys.exit("the brief %s is empty" % path)
    return text


def check_tool_api(path):
    try:
        spec = json.load(open(path))
    except Exception as e:
        sys.exit("the tool API file %s is not JSON: %s" % (path, e))
    if not spec.get("servers") or not spec.get("paths"):
        sys.exit("the tool API file %s has no servers or paths" % path)
    return spec


def _xml_text(xml):
    return re.sub(r"<[^>]+>", "", xml)


def read_text(p):
    """Text of one document, or None when there is no way to get text from it here."""
    p = pathlib.Path(p)
    ext = p.suffix.lower()
    if ext in TEXT:
        raw = p.read_bytes()
        for enc in ("utf-8-sig", "cp1254"):       # Turkish Windows files are often cp1254
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                pass
        return raw.decode("utf-8", "replace")
    if ext == ".docx":
        z = zipfile.ZipFile(p)
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = xml.replace("</w:p></w:tc>", "</w:tc>").replace("</w:tc>", " | ").replace("</w:p>", "\n").replace("<w:tab/>", "\t").replace("<w:br/>", "\n")
        return _xml_text(xml)
    if ext == ".xlsx":
        z = zipfile.ZipFile(p)
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            shared = [_xml_text(si) for si in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8", "ignore"), re.S)]
        wb = z.read("xl/workbook.xml").decode("utf-8", "ignore")
        sheets = re.findall(r'<sheet [^>]*name="([^"]*)"', wb)
        out = []
        for i, name in enumerate(sorted([n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)], key=lambda n: int(re.findall(r"\d+", n)[0]))):
            out.append("### sheet: %s" % (sheets[i] if i < len(sheets) else name))
            for row in re.findall(r"<row [^>]*>(.*?)</row>", z.read(name).decode("utf-8", "ignore"), re.S):
                cells = []
                for attrs, body in re.findall(r"<c ([^>]*?)(?:/>|>(.*?)</c>)", row, re.S):
                    v = re.search(r"<v>(.*?)</v>", body or "", re.S)
                    t = re.search(r't="(\w+)"', attrs)
                    if t and t.group(1) == "s" and v:
                        cells.append(shared[int(v.group(1))] if int(v.group(1)) < len(shared) else "")
                    elif t and t.group(1) == "inlineStr":
                        cells.append(_xml_text(body or ""))
                    else:
                        cells.append(v.group(1) if v else "")
                out.append(" | ".join(cells))
        return "\n".join(out)
    if ext == ".pdf":
        try:
            import pypdf
            return "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(str(p)).pages)
        except Exception:
            return None
    return None


OBLIG = re.compile(r"\b(must|never|always|only|shall|should|cannot|can't|do not|don't|not allowed|required|at most|at least|exactly|maximum|minimum|once|twice|three times|no more than|not more than|asla|mutlaka|yalnızca|sadece|gerekir|zorunlu|yasak|en fazla|en az)\b", re.I)
CHANGE = re.compile(r"\b(correction|instead of|no longer|please build to|build to these|supersede[sd]?|replaces|won't show|doesn't show|not yet in|changed|decided|agreed|from now on|update:|rather than|not .{1,25}, but|yerine|artık|düzeltme|karar verildi)\b", re.I)
OPEN = re.compile(r"\b(open point|not agreed|tbd|to confirm|unclear|no answer|not decided|to be decided|still open|undecided|no promises)\b", re.I)
QUOTED = re.compile(r"[\"“]([^\"”]{18,200})[\"”]")
TURN = re.compile(r"^\[(\d\d:\d\d:\d\d)\] ([^:]{2,40}): (.*)$")
DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def condense(text):
    """A meeting transcript without its small talk: a turn is kept when it is long, has a number, a quote, or an obligation, change or open-point
    word. Header lines stay. Returns (text, dropped turns)."""
    out, dropped = [], 0
    for line in text.splitlines():
        m = TURN.match(line)
        if not m:
            out.append(line)
            continue
        who, said = m.group(2), m.group(3)
        if len(said) >= 70 or re.search(r"\d", said) or '"' in said or OBLIG.search(said) or CHANGE.search(said) or OPEN.search(said):
            out.append("%s: %s" % (who, said))
        else:
            dropped += 1
    return "\n".join(out), dropped


def doc_kind(rel, text):
    n = rel.lower()
    if sum(1 for l in text[:4000].splitlines() if TURN.match(l)) >= 3:        # timestamped speaker turns, whatever the file is called
        return "meeting transcript"
    for key, kind in (("contract", "service contract"), ("analysis", "analysis"), ("faq", "faq (public page)"), ("prompt", "phone-menu prompt sheet"),
                      ("readme", "pack overview"), ("brief", "task brief"), ("test-customers", "test data")):
        if key in n:
            return kind
    if "transcript" in n:
        return "meeting transcript"
    if re.match(r"(?m)^(From|To|Subject):", text[:600]):
        return "e-mail thread"
    return "document"


def doc_date(rel, text):
    m = DATE_IN_NAME.search(rel)
    if m:
        return m.group(1)
    m = re.search(r"(?m)^Date:.*?(\d{1,2}) (\w{3}) (\d{4})", text[:800])
    if m:
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        mm = months.index(m.group(2)[:3].lower()) + 1 if m.group(2)[:3].lower() in months else 0
        if mm:
            return "%s-%02d-%02d" % (m.group(3), mm, int(m.group(1)))
    return "undated"


def digest(corpus_text, docs):
    """A map of the corpus for the agent: the documents newest first, and the lines (numbers in corpus.md) that change earlier text, leave a point open,
    or hold quoted wording. Deterministic; it finds where to look, the agent decides what it means. docs: {rel: (kind, date)}."""
    lines = corpus_text.splitlines()
    cur, spans = None, {}
    for i, line in enumerate(lines, 1):
        m = re.match(r"=== FILE: (.*) ===$", line)
        if m:
            cur = m.group(1)
            spans[cur] = [i, i]
        elif cur:
            spans[cur][1] = i
    order = sorted(docs, key=lambda r: docs[r][1] if docs[r][1] != "undated" else "0000", reverse=True)
    out = ["# Map of the corpus (made by code; line numbers are lines of corpus.md)", "",
           "## Documents, newest first (read in this order; where documents disagree, the newer one wins unless it says otherwise)", "",
           "| document | kind | date | lines |", "|---|---|---|---|"]
    for rel in order:
        a, b = spans.get(rel, (0, 0))
        out.append("| %s | %s | %s | %d-%d |" % (rel, docs[rel][0], docs[rel][1], a, b))

    def where(i):
        for rel, (a, b) in spans.items():
            if a <= i <= b:
                return rel
        return "?"

    def pick(rx, limit):
        found = []
        for i, line in enumerate(lines, 1):
            if line.startswith("=== FILE:") or len(line.strip()) < 25 or not rx.search(line):
                continue
            found.append((docs.get(where(i), ("", "undated"))[1], i, line.strip()))
        found.sort(key=lambda t: (t[0] if t[0] != "undated" else "0000", -t[1]), reverse=True)
        return ["- L%d (%s): %s" % (i, where(i).rsplit("/", 1)[-1], t[:170]) for _, i, t in found[:limit]]

    for title, rx, limit in (("Lines that change or correct earlier text (newest first)", CHANGE, 50), ("Points left open", OPEN, 30)):
        out += ["", "## " + title, ""] + (pick(rx, limit) or ["- none found"])
    quoted = [(i, m.group(1)) for i, line in enumerate(lines, 1) for m in [QUOTED.search(line)] if m and not line.startswith("===")]
    out += ["", "## Quoted wording (candidates for `wording` rules)", ""] + ["- L%d (%s): %s" % (i, where(i).rsplit("/", 1)[-1], q[:170]) for i, q in quoted[:60]]
    return "\n".join(out) + "\n"


def ingest_folder(folder, dest):
    """Copies a case folder into dest/original and writes dest/corpus.md: every document with a text copy, in reading order (BRIEF.md,
    README.md, then the rest by name), each under a `=== FILE: name ===` header. Documents with no text copy (images, PDFs that cannot be
    read here) are listed so the agent reads them itself. Returns {"corpus", "documents", "unconverted", "contract"}."""
    root = pathlib.Path(folder)
    if not root.is_dir():
        sys.exit("case folder not found: %s" % folder)
    files = [f for f in root.rglob("*") if f.is_file() and not any(part.startswith((".", "__MACOSX")) for part in f.relative_to(root).parts)]
    files.sort(key=lambda f: (FIRST.index(f.name.lower()) if f.name.lower() in FIRST else len(FIRST), str(f.relative_to(root)).lower()))
    if not files:
        sys.exit("the case folder %s has no documents" % folder)
    dest = pathlib.Path(dest)
    (dest / "original").mkdir(parents=True, exist_ok=True)
    parts, documents, unconverted, visual, data, contract = [], [], [], [], [], None
    docs_meta = {}
    for f in files:
        rel = str(f.relative_to(root))
        target = dest / "original" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f.read_bytes())
        documents.append(rel)
        if f.suffix.lower() in IMAGES or f.suffix.lower() == ".pdf":
            visual.append(rel)          # a drawing's extracted text lists the boxes and loses the arrows: the agent looks at it
        text = read_text(f)
        if text is None or not text.strip():
            unconverted.append(rel)
            continue
        if f.suffix.lower() in DATA and len(text) > BIG:
            data.append(rel)
            head = "\n".join(text.strip().splitlines()[:25])
            parts.append("=== FILE: %s ===\n(data file, %d bytes, not copied here: open input/original/%s and look up what you need. It starts:)\n%s\n" % (rel, len(text), rel, head))
            docs_meta[rel] = ("test data", doc_date(rel, text))
            continue
        kind = doc_kind(rel, text)
        if kind == "meeting transcript":
            text, dropped = condense(text)
            if dropped:
                text += "\n(%d turns of small talk are left out here; the whole transcript is in input/original/%s)" % (dropped, rel)
        parts.append("=== FILE: %s ===\n%s\n" % (rel, text.strip()))
        docs_meta[rel] = (kind, doc_date(rel, text))
        if f.suffix.lower() == ".json" and contract is None:
            try:
                spec = json.loads(text)
                if spec.get("paths") and spec.get("servers"):
                    contract = "input/original/" + rel
            except Exception:
                pass
    if not parts and not visual:
        sys.exit("no document in %s could be read" % folder)
    corpus = "\n".join(parts) or "(no document had a text copy; read the documents listed under visual)\n"
    (dest / "corpus.md").write_text(corpus)
    (dest / "digest.md").write_text(digest(corpus, docs_meta))
    return {"corpus": "input/corpus.md", "documents": documents, "unconverted": unconverted, "visual": visual, "data": data, "contract": contract}
