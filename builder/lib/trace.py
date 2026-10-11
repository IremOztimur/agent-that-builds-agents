"""Plain-text trace of one build, as the hackathon asks: start and end time, every model call (model and what it was asked), the
Freya objects created, and every self-test with its result. The file is opened for appending so tools/practice.py can add
platform events (for example the one-simulation-at-a-time limit) to the same trace."""
import time


class Trace:
    def __init__(self, path):
        self.path = path
        self.line("start", time.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def line(self, kind, text):
        with open(self.path, "a") as f:
            f.write("%s | %-8s | %s\n" % (time.strftime("%H:%M:%S"), kind, str(text).replace("\n", " ")[:400]))
