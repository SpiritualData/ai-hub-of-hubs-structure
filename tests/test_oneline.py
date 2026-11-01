"""The one-line functions run for real, offline: network arms get recorded or fake transports, the model is a fake provider.
The live check at the bottom is skipped unless HUBOFHUBS_LIVE is set and is NOT run by the suite."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs  # noqa: E402
from hubofhubs import Needs, cli  # noqa: E402
from hubofhubs.card import Card  # noqa: E402
from hubofhubs.cardstore import LocalCardStore  # noqa: E402
from hubofhubs.ports.events import EVENT_DECISION, EVENT_DONE, EVENT_RESULT, EVENT_WORK_TRACE  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class Reply:
    def __init__(self, body, status=200):
        self.body, self.status_code, self.text = body, status, json.dumps(body)

    def json(self):
        return self.body


def serper_http(method, url, **kwargs):
    return Reply({"organic": [{"title": "Rust 1.90.0 released", "link": "https://blog.rust-lang.org/2025/09/18/Rust-1.90.0/", "snippet": "The Rust team announces 1.90.0."}],
                  "answerBox": {"answer": "1.90.0"}})


class FakeProvider:
    tokens_in = tokens_out = 0

    def answer(self, messages, *, model=None, system=None, layers=None):
        self.tokens_in, self.tokens_out = 12, 5
        return f"echo[{model}]: {messages[-1]['content']}"

    def list_models(self):
        return ["fake"]

    def plan(self, *a, **k):
        raise NotImplementedError

    def supports_web_search(self, model=None):
        return False

    def web_search(self, *a, **k):
        raise NotImplementedError


def test_ask_is_grounded_in_the_search_seat_and_carries_sources():
    result = hubofhubs.run("what is the latest Rust release?", arms={"search-backend": "serper"},
                           options={"search-backend": {"http": serper_http}}, environ={"SERPER_API_KEY": "k"})
    assert result.seat == "search-backend" and result.answer == "1.90.0" and result.note == ""
    assert result.items[0]["url"].startswith("https://blog.rust-lang.org/")
    with pytest.raises(Needs, match="GEMINI_API_KEY"):      # no key: never a silent fall back to the model's memory
        hubofhubs.run("what is the latest Rust release?", environ={})


def test_model_seat_uses_the_call_a_model_arm_reports_tokens_and_says_it_has_no_sources():
    seen = []
    result = hubofhubs.run("what is the latest Rust release?", "model", provided={"call-a-model": FakeProvider()}, environ={}, on_event=seen.append)
    assert result.note.startswith("answered from the model only") and result.items == ()
    assert result.answer == "echo[None]: what is the latest Rust release?" and str(result) == result.answer
    assert result.seat == "model-call" and result.tokens == {"in": 12, "out": 5}
    assert [e.type for e in result.events] == [e.type for e in seen] and result.events[-1].type == EVENT_DONE
    assert json.dumps(result.to_dict())


def test_search_runs_the_selected_search_arm_and_traces_the_work():
    result = hubofhubs.run("latest Rust release", "search", arms={"search-backend": "serper"},
                           options={"search-backend": {"http": serper_http}}, environ={"SERPER_API_KEY": "k"})
    assert result.answer == "1.90.0" and result.items[0]["title"] == "Rust 1.90.0 released"
    assert result.arms["search-backend"] == "serper"
    states = [t["state"] for t in result.trace]
    assert states == ["running", "done"] and result.trace[-1]["items"][0]["ref"] == "blog.rust-lang.org"   # a domain, never the full url


def test_papers_runs_the_scholarly_arm_on_a_recorded_response():
    body = json.loads((FIXTURES / "openalex_works_search.json").read_text(encoding="utf-8"))
    seen = []

    def transport(url, *, params, headers, timeout):
        seen.append(url)
        return Reply(body)
    result = hubofhubs.run("meditation and attention", "papers", arms={"know-the-world": "openalex"},
                           options={"know-the-world": {"transport": transport, "min_interval": 0}}, environ={})
    assert seen and result.items and result.items[0].get("title") and result.trace[-1]["state"] == "done"


def test_recall_finds_a_stored_card(tmp_path):
    store = LocalCardStore(str(tmp_path / "cards.db"))
    store.add(Card(id="a", text="Rust 1.90 is the release in these notes", source="notes", tags=("rust",)))
    result = hubofhubs.run("Rust release", "recall", provided={"card-store": store}, environ={})
    assert [i["id"] for i in result.items] == ["a"] and "1.90" in result.answer


def test_a_seat_that_lacks_a_key_says_exactly_what_to_set():
    seen = []
    with pytest.raises(Needs) as raised:
        hubofhubs.run("latest Rust release", "search", environ={}, on_event=seen.append)
    assert "GEMINI_API_KEY" in str(raised.value) and raised.value.seat == "search-backend"
    ask = [e for e in seen if e.type == EVENT_DECISION]
    assert ask and ask[0].decision_id == "needs-setup" and ask[0].data["lines"] and seen[-1].type == EVENT_DONE
    assert not [e for e in seen if e.type == EVENT_RESULT]


def test_needs_lists_the_lines_for_a_seat_and_the_seats_it_needs():
    lines = hubofhubs.needs("papers", environ={})
    assert any("GEMINI_API_KEY" in line for line in lines) and len(lines) == 2
    assert hubofhubs.needs("search", arms={"search-backend": "serper"}, environ={"SERPER_API_KEY": "k"}) == ()


def test_stream_is_the_core_and_yields_live():
    gen = hubofhubs.stream("Rust", "search", arms={"search-backend": "serper"}, options={"search-backend": {"http": serper_http}}, environ={"SERPER_API_KEY": "k"})
    first = next(gen)
    assert first.type == "status"
    rest = [e.type for e in gen]
    assert rest[-2:] == [EVENT_RESULT, EVENT_DONE] and EVENT_WORK_TRACE in rest


def test_environ_defaults_to_the_process_environment(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    assert hubofhubs.needs("search", arms={"search-backend": "serper"})
    monkeypatch.setenv("SERPER_API_KEY", "k")
    assert hubofhubs.needs("search", arms={"search-backend": "serper"}) == ()
    assert hubofhubs.needs("search", arms={"search-backend": "serper"}, environ={})   # an explicit mapping replaces it
    assert "search-backend" in hubofhubs.assemble(arms={"search-backend": "serper"})


def test_assemble_takes_no_required_argument_and_a_lock():
    assert "card-store" in hubofhubs.assemble()
    lock = {"schema": "esoi.lock/1", "solutions": {"card-store": {"arm": "local_card_store"}}}
    assert "card-store" in hubofhubs.assemble(lock=lock)


def test_the_cli_is_a_thin_wrapper(capsys):
    code = cli.main(["run", "latest Rust release", "--seat", "search", "--json"])
    assert code == 2 or code == 0   # 2 without a key in this environment
    out = capsys.readouterr().out.strip().splitlines()
    assert all(json.loads(line) for line in out) and json.loads(out[-1]).get("type") in ("done", "run")


def test_unknown_seat_names_the_choices():
    with pytest.raises(ValueError, match="ask"):
        hubofhubs.run("x", "nonsense")


@pytest.mark.skipif(not os.environ.get("HUBOFHUBS_LIVE"), reason="live check: real search and model calls; not run by the suite")
def test_live_grounded_ask_and_model_seat():
    """RUN LIVE on 2026-11-01 (passed): the Gemini key from the environment, the search arm gemini; the model seat through the
    Claude Code subscription (claude_cli, haiku), never the paid API. `run("what is the latest Rust release?")` answered
    "The latest stable release of Rust is version 1.99.1" with four sources, and the version matched the stable line of releases.rs."""
    grounded = hubofhubs.run("what is the latest Rust release?")
    assert grounded.answer and grounded.items and grounded.arms["search-backend"] == "gemini" and not grounded.note
    alone = hubofhubs.run("Reply with the single word: ok", "model", model="claude-haiku")
    assert alone.answer and alone.note and alone.items == ()
