"""Plain-text trace of one build: start and end, phases, each model turn, self-tests, Freya objects."""
import time


class Trace:
    def __init__(self, path):
        self.f = path.open("w")
        self.line("start", time.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def line(self, kind, text):
        self.f.write("%s | %-8s | %s\n" % (time.strftime("%H:%M:%S"), kind, str(text).replace("\n", " ")[:400]))
        self.f.flush()
