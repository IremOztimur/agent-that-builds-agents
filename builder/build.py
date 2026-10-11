"""The builder: reads a bank brief and its tool API file, creates the phone agent on Freya. No manual step.

    python3 builder/build.py <brief file, any name> <tool API file, any name> [--slot NAME] [--cases A|B|AB] [--minutes 25] [--fresh] [--prepare-only]

One agent session works through three phases in order (read-brief, compose-workflow, test-and-repair); code checks each phase before the next starts. See builder/lib/.
--fresh builds into a new Freya workflow and agent (the slot name gets a timestamp) instead of updating the slot in place.
Needs FREYA_API_KEY, FREYA_BANK_TEAM_KEY and a Claude login (or ANTHROPIC_API_KEY); BUILDER_MODEL picks the model.
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from builder.lib import pipeline


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    opt = {argv[i]: argv[i + 1] for i in range(2, len(argv) - 1) if argv[i].startswith("--")}
    brief, api = argv[0], argv[1]
    work, result = pipeline.build(brief, api, opt.get("--slot") or pathlib.Path(brief).stem, opt.get("--cases", "AB"),
                                  int(opt.get("--minutes", 25)), "--prepare-only" in argv, "--fresh" in argv)
    print(work if "--prepare-only" in argv else json.dumps(result or {"failed": True}))


if __name__ == "__main__":
    main(sys.argv[1:])
