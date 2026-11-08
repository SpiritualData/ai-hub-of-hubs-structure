"""Write ``cases.json`` for the hub's solution relevance: the hand-labelled cases of ``hand_cases.json`` (requests the hub's
consumers send, outside candidates, bug reports) and the cases mined from this repository's git history by the esoi library's
miner (a commit subject in, the solutions whose code it changed out). Run it deliberately; the case digest then changes.
"""
import json
from pathlib import Path

from esoi.structure.intent_registry import config as config_module, registry
from esoi.understanding.solution_relevance import relevance_cases

HERE = Path(__file__).resolve().parent


def main() -> None:
    config = config_module.load(HERE.parents[1])
    hand = json.loads((HERE / "hand_cases.json").read_text(encoding="utf-8"))
    cases = relevance_cases.build(config, registry.load(config), hand, limit=600)
    for case in cases:
        if case["kind"] == "git":
            case["id"] = "hub-" + case["id"]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases ({len(hand)} by hand)")


if __name__ == "__main__":
    main()
