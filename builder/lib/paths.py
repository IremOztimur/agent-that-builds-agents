"""Fixed locations."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BUILDER = ROOT / "builder"
KIT = ROOT / "build-the-builder_pack"
SLOTS = BUILDER / ".slots.json"
