"""Sets the abstention floor (``hubofhubs.retrieval.abstain.CONFIDENCE_FLOOR``) before any arm is scored.

Positives are the subjects of the 100 newest commits of the history that older cases may learn from (requests that do need the corpus);
negatives are ``datasets/no_context_validation.json`` (requests that do not). The scored cases (the 150 newer commits and ``no_context.json``)
are never read here. The floor is the confidence that maximises the mean of the two recalls (balanced accuracy); ties take the lower floor.

    PYTHONPATH=.:evaluation:../evolvable-structure/implementations/python ESOI_OFFLINE=1 python3 evaluation/context_retrieval/calibrate.py
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_retrieval.score import DATASETS, world  # noqa: E402
from hubofhubs.retrieval.abstain import confidence  # noqa: E402
from hubofhubs.retrieval.fusion import HybridRrf  # noqa: E402


def main():
    state = world()
    hybrid = HybridRrf()
    hybrid.prepare(state["files"], state["history"])
    newest = sorted(state["history"], key=lambda c: str(c.get("date", "")), reverse=True)[:100]
    positives = [confidence(hybrid, c["subject"]) for c in newest]
    negatives = [confidence(hybrid, c["task"]) for c in json.loads((DATASETS / "no_context_validation.json").read_text())]
    best = None
    for floor in sorted(set(round(x, 3) for x in positives + negatives)):
        score = (sum(p >= floor for p in positives) / len(positives) + sum(n < floor for n in negatives) / len(negatives)) / 2
        if best is None or score > best[0] + 1e-9:
            best = (score, floor)
    print(f"positives {len(positives)} (median {statistics.median(positives):.3f}), negatives {len(negatives)} (median {statistics.median(negatives):.3f})")
    print(f"floor {best[1]} balanced accuracy {best[0]:.3f}")


if __name__ == "__main__":
    main()
