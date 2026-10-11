"""Where the inputs are. The harness writes inputs.json next to the tools: {"brief": "input/<name>", "tools": "input/<name>", "brief_lines": N}.

    from inputs import brief_path, tools_path, brief_lines
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_m = json.load(open(ROOT / "inputs.json")) if (ROOT / "inputs.json").exists() else {}


def brief_path():
    return ROOT / _m.get("brief", "brief.md")


def tools_path():
    """The tool API file, or None when the case folder has no machine-readable contract (the agent reads it as a document)."""
    return ROOT / _m["tools"] if _m.get("tools") else None


def meta():
    return _m


def mode():
    return _m.get("mode", "dev")


def base_url():
    """Where the tools may call: the mock URL in the final, the server of the tool API file in development."""
    if _m.get("base_url"):
        return _m["base_url"].rstrip("/")
    try:
        return json.load(open(tools_path()))["servers"][0]["url"].rstrip("/")
    except Exception:
        return None


def brief_lines():
    return _m.get("brief_lines")
