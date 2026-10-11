"""Reads the two inputs, whatever they are called, and fails loudly when one cannot be used."""
import json, pathlib, re, sys, zipfile


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
