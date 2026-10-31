"""The search-backend and know-the-world components: the matching rules, the baselines they must fail, and the cases."""
import importlib
import json
import sys
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
from know_the_world import score as papers  # noqa: E402
from search_backend import score as sources  # noqa: E402

GOLD = ["https://en.wikipedia.org/wiki/Paya,_Boyac%C3%A1", "https://www.example.org/a/b/"]


@pytest.mark.parametrize("url,title,expected", [
    ("https://en.wikipedia.org/wiki/Paya,_Boyac%C3%A1#History", "", True),      # page match: fragment ignored
    ("https://en.wikipedia.org/wiki/Other_Town", "", False),                    # Wikipedia needs the page
    ("http://example.org/a/b", "", True),                                       # scheme, www and trailing slash ignored
    ("https://example.org/somewhere/else", "", True),                           # domain match
    ("https://other.example.org/a/b", "", False),                               # another host
    ("https://vertexaisearch.cloud.google.com/grounding-api-redirect/xyz", "example.org", True),   # unresolved link read by title
    ("https://vertexaisearch.cloud.google.com/grounding-api-redirect/xyz", "en.wikipedia.org", False),
    ("https://vertexaisearch.cloud.google.com/grounding-api-redirect/xyz", "a nice title", False),
])
def test_matching_rule(url, title, expected):
    assert sources.from_gold_source(url, GOLD, title) is expected


def test_an_arm_without_its_credential_is_not_measured(monkeypatch):
    for name in ("SEARXNG_URL", "BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    from hubofhubs.websearch.backends import BraveBackend, SearxngBackend
    for arm in (BraveBackend, SearxngBackend):
        with pytest.raises(sources.NoCredential, match="not measured: no credential"):
            sources.settings_for(arm)


def test_a_title_in_the_question_is_not_a_find():
    from hubofhubs.ports.retrieval import Observation
    case = dict(question="Is there a paper called Attention Is All You Need?", gold_title="Attention Is All You Need")
    echoed = Observation(kind="query", text='WORKS for "Is there a paper called Attention Is All You Need?": no matching works.')
    found = Observation(kind="query", text="1. Attention is all you need. Vaswani 2017", hits=[{"title": "Attention Is All You Need"}])
    assert papers.score_case(lambda kind, args: echoed, case)["ok"] is False
    assert papers.score_case(lambda kind, args: found, case)["ok"] is True


@pytest.mark.parametrize("component,baseline", [("search_backend", "wikipedia_guess"), ("know_the_world", "echo_question")])
def test_the_baseline_fails_the_cases(component, baseline):
    score = importlib.import_module(f"{component}.score")
    fn = importlib.import_module(f"{component}.broken.{baseline}").build(None)
    cases = json.loads((EVALUATION / component / "cases.json").read_text())
    passed = sum(bool(score.score_case(fn, case)["ok"]) for case in cases)
    assert passed < len(cases) / 2


@pytest.mark.parametrize("component", ["search_backend", "know_the_world"])
def test_at_least_thirty_cases_with_unique_ids(component):
    cases = json.loads((EVALUATION / component / "cases.json").read_text())
    assert len(cases) >= 30 and len({c["id"] for c in cases}) == len(cases)
