"""Fixed locations."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BUILDER = ROOT / "builder"
KIT = BUILDER / "kit"        # the hackathon kit files the builder needs, vendored so the commit runs on its own
SLOTS = BUILDER / ".slots.json"
