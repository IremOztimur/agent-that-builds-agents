"""Reads the inputs, whatever they are called, and fails loudly when one cannot be used.
A single brief file plus a tool API file (development), or a case folder of documents (the final): Markdown, text, Word, Excel, PDF, images."""
import json, pathlib, re, sys, zipfile

TEXT = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html", ".htm", ".xml", ".tsv"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
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
    parts, documents, unconverted, visual, contract = [], [], [], [], None
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
        parts.append("=== FILE: %s ===\n%s\n" % (rel, text.strip()))
        if f.suffix.lower() == ".json" and contract is None:
            try:
                spec = json.loads(text)
                if spec.get("paths") and spec.get("servers"):
                    contract = "input/original/" + rel
            except Exception:
                pass
    if not parts and not visual:
        sys.exit("no document in %s could be read" % folder)
    (dest / "corpus.md").write_text("\n".join(parts) or "(no document had a text copy; read the documents listed under visual)\n")
    return {"corpus": "input/corpus.md", "documents": documents, "unconverted": unconverted, "visual": visual, "contract": contract}
