"""A step the answer depends on and a step that only enriches it: the first reports its failure, the second never fails the answer."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from hubofhubs.the_intelligence.mind.delegation.delegation import SUPPORTING, ToTools  # noqa: E402
from hubofhubs.the_intelligence.mind.flow import failed_pieces  # noqa: E402
from hubofhubs.the_self.steps import DONE, SUPPORTING as SUPPORTING_KIND, UNAVAILABLE, Step, support, take  # noqa: E402


class Broken:
    def enrich(self, **arguments):
        raise ConnectionRefusedError("the network refused")


def test_a_supporting_step_that_raises_is_unavailable_and_says_it_is_supporting():
    found = support(Broken(), "web-search", method="enrich")
    assert (found.status, found.depends) == (UNAVAILABLE, SUPPORTING_KIND) and "refused" in found.reason
    assert found.to_dict()["depends"] == "supporting"


def test_a_supporting_step_that_works_is_done():
    class Fine:
        def enrich(self, **arguments):
            return {"ok": True}
    found = support(Fine(), "web-search", method="enrich")
    assert found.status == DONE and found.output == {"ok": True}


def test_a_step_the_answer_depends_on_reports_its_failure():
    with pytest.raises(ConnectionRefusedError):
        take(Broken(), "web-search", method="enrich")


def test_a_required_step_is_not_marked_supporting():
    assert "depends" not in Step("the-mind", DONE).to_dict()


class Tools:
    def __init__(self, fail):
        self.fail = fail

    def use(self, category, request, cancel_check=None, authority=None):
        raise self.fail


def delegate(category):
    piece = {"piece": "do it", "tool": category, "sub_goal": None}
    return ToTools(Tools(ConnectionRefusedError("refused")), None).delegate([piece], authority={"allow": [category]})[0]


@pytest.mark.parametrize("category", sorted(SUPPORTING))
def test_a_worker_that_only_enriches_is_unavailable_with_how_to_enable_it_and_is_no_failed_piece(category):
    row = delegate(category)
    assert row["unavailable"] == SUPPORTING[category][0] and row["how"] and "error" not in row
    assert failed_pieces([row]) == []


def test_a_worker_the_answer_depends_on_is_an_error():
    row = delegate("file-editing")
    assert "error" in row and "unavailable" not in row
    assert failed_pieces([row]) == [row]
