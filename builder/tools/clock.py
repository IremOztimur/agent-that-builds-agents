"""Minutes left on the builder clock.   python3 tools/clock.py"""
import os, time
d = float(os.environ.get("BUILDER_DEADLINE", "0") or 0)
print("%.1f minutes left" % ((d - time.time()) / 60) if d else "no clock set")
