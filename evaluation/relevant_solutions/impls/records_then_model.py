"""The hub's records_then_model arm of Relevant Solutions over this hub's records (the library's lexical candidates, then one cheap model call),
each solution then the nearest scope above it (role parent). One model call per case at the cheap tier; run only with --max-calls."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAID = True


def build(meter):
    sys.path.insert(0, str(ROOT / "evaluation"))
    from solution_passes.score import Plumbing
    from hubofhubs.api import RecordsThenModel
    arm = RecordsThenModel(Plumbing(meter))

    def classify(text):
        found = arm.relevant(text, str(ROOT))["solutions"]
        out = [{"solution_id": f["solution_id"], "score": f["score"], "role": "solution"} for f in found]
        seen = {f["solution_id"] for f in found}
        for item in found:
            parent = (item.get("chain") or [""])[0]
            if parent and parent not in seen:
                seen.add(parent)
                out.append({"solution_id": parent, "score": 0.0, "role": "parent"})
        return out
    return classify
