"""The hub's own Relevant Solutions arm (records_index) over this hub's records: each relevant solution, then the nearest scope above each
(role parent, counted for recall and not against precision). Zero model calls."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def build(meter):
    from hubofhubs.api import RecordsIndex
    arm = RecordsIndex()

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
