"""Where the inputs are. The harness writes inputs.json next to the tools: {"brief": "input/<name>", "tools": "input/<name>", "brief_lines": N}.

    from inputs import brief_path, tools_path, brief_lines
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_m = json.load(open(ROOT / "inputs.json")) if (ROOT / "inputs.json").exists() else {}


def brief_path():
    return ROOT / _m.get("brief", "brief.md")


def tools_path():
    return ROOT / _m.get("tools", "tools.json")


def brief_lines():
    return _m.get("brief_lines")
