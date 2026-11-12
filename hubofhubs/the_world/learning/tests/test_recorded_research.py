"""recorded_research on a folder store: a first question is recorded with its knowledge and context item, a related one reuses it, a stale one is extended in place."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "evaluation"))
from research_recorded import score  # noqa: E402

from hubofhubs.the_world.learning.recorded_research import RecordedResearch  # noqa: E402
from hubofhubs.the_world.learning.research_freshness_reader.registry import RegistryScan  # noqa: E402
from hubofhubs.the_world.learning.research_ports import FolderKnowledge, FolderStore  # noqa: E402

CASES = {c["id"]: c for c in score.load_cases()}


def arm(root, context, judge=""):
    return RecordedResearch(freshness=RegistryScan(), science=score.Counting(score.FakeScience(CASES["first-complete-standard"]["args"]["science"])),
                            web=score.Counting(score.FakeWeb(CASES["first-complete-standard"]["args"]["web"])), plumbing=None, ask=lambda prompt: json.dumps({"answered_by": judge}),
                            store=FolderStore(root), knowledge=FolderKnowledge(root), context=context, placer=lambda question, decision: ["sol-a"])


def test_first_then_related_then_stale(tmp_path):
    score.seed(tmp_path)
    context = score.Context()
    review = dict(CASES["first-complete-standard"]["args"]["review"], root=str(tmp_path))
    first = arm(tmp_path, context).review(**review)
    assert first["recorded"] and first["gaps"] == [] and not first["reused"] and context.items[0]["solution_ids"] == ["sol-a"]
    assert {k["solution_ids"] for k in score.knowledge_rows(tmp_path)} == {"sol-a"}
    again = arm(tmp_path, context, judge=first["investigation"]["investigation_id"]).review(**dict(review, question="a differently worded question about the same libraries"))
    assert again["reused"] and not again["searched"] and again["cited"]["done_on"] == "2026-11-10"
    later = arm(tmp_path, context).review(**dict(review, today="2027-03-01"))
    assert later["updated"] and later["investigation"]["investigation_id"] == first["investigation"]["investigation_id"]
    with open(tmp_path / "hubofhubs" / "registry" / "investigations.csv", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 1
