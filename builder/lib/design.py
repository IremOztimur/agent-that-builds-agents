"""The phase 1 gate on design.json. The check itself lives in tools/check_design.py, so the agent can run the same one before it finishes the phase."""
import sys

from .paths import BUILDER

sys.path.insert(0, str(BUILDER / "tools"))
from check_design import DENSITY, SIZE, check   # noqa: E402,F401
