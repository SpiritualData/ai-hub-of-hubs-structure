"""The real stage of the Learning metric: one real review through the assembled hub on a plain install (a logged-in Claude CLI, no vendor key). Web search runs through the Claude login arm (no key). Quick size by
default: the question is about terminal agent libraries, the model is the fast tier. It prints the record's summary and the gaps. Paid-optional: it spends only
the subscription's calls (two web or model calls and at most two model calls for screening and synthesis). Run: PYTHONPATH=../evolvable-structure/implementations/python
python3 evaluation/learning_review/real_stage.py [--size quick|standard]. The small stage (three real reviews) is this script run with three questions and a call budget."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

QUESTION = "Which open-source terminal agent libraries are adoptable for a Python terminal UI?"
DECISION = "adopt an existing library as an arm, or write one"


def main(argv):
    from hubofhubs.api import AssemblyConfig, assemble
    import hubofhubs.the_world.learning.systematic_review  # noqa: F401  (declares the arm; the selection snapshot is regenerated at commit)
    size = argv[argv.index("--size") + 1] if "--size" in argv else "quick"
    system = assemble(config=AssemblyConfig(solutions=("the-learning", "model-plumbing"), names={"the-learning": "systematic_review", "web-search": "claude_login", "vendor-model-caller": "claude_cli"}))
    got = system["the-learning"].review(QUESTION, DECISION, weight=size, links=["solution:terminal-experience"], intent_id="the-world",
                                        criteria={"exclude_terms": ["tutorial for beginners"], "since": "2025-01-01"}, use_model=True)
    row = got["investigation"]
    print(json.dumps({k: row[k] for k in ("investigation_id", "size", "protocol_date", "sources", "found", "screened_out", "kept", "decisions", "refresh_on",
                                         "synthesis_known", "synthesis_contested", "synthesis_unknown", "limitations")}, indent=1))
    print("queries:", row["queries"])
    for item in got["items"]:
        print(item["item_id"], item["grade"], item["independent"], item["verified"], item["licence"], item["source"], "|", item["applied"])
    print("gaps:", got["gaps"])
    return 0 if not got["gaps"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
