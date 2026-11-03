"""The one-line functions run for real, offline: network arms get recorded or fake transports, the model is a fake provider.
The live check at the bottom is skipped unless HUBOFHUBS_LIVE is set and is NOT run by the suite."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs  # noqa: E402
from esoi.entry import Pending  # noqa: E402
from hubofhubs import cli  # noqa: E402
from hubofhubs.seats import CardStore, WholeAnswering  # noqa: E402
from hubofhubs.card import Card  # noqa: E402
from hubofhubs.cardstore import LocalCardStore  # noqa: E402
from hubofhubs.ports.events import EVENT_DONE, EVENT_RESULT, EVENT_WORK_TRACE  # noqa: E402

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


def whole_hub(tmp_path, **extra):
    """The whole hub with the search arm on a recorded response and a fake model: no key, no program, no network."""
    keywords = dict(arms={"search-backend": "serper", "act-in-the-world": "fast_edit"},
                    options={"search-backend": {"http": serper_http}},
                    provided={"call-a-model": FakeProvider()},
                    environ={"SERPER_API_KEY": "k", "HUBOFHUBS_WRITE_ROOT": str(tmp_path)})
    keywords.update(extra)
    return keywords


def test_run_the_whole_hub_answers_with_sources_and_holds_the_answer_to_them(tmp_path):
    result = hubofhubs.run("hub-of-hubs", "what is the latest Rust release?", **whole_hub(tmp_path))
    assert result.seat == "assemble-the-whole" and result.answer == "1.90.0" and result.note == ""
    assert result.items[0]["url"].startswith("https://blog.rust-lang.org/")
    assert [t["state"] for t in result.trace] == ["running", "done"] and result.events[-1].type == EVENT_DONE
    assert [e.type for e in result.events].count(EVENT_RESULT) == 1 and json.dumps(result.to_dict()) and str(result) == "1.90.0"


def test_the_whole_hub_without_a_key_says_exactly_what_to_set():
    with pytest.raises(Pending) as raised:
        hubofhubs.run("hub-of-hubs", "what is the latest Rust release?", environ={})
    text = str(raised.value)
    assert "GEMINI_API_KEY" in text and "HUBOFHUBS_WRITE_ROOT" in text      # nothing is attempted; each line says what to set
    assert {r.kind for r in raised.value.reasons} <= {"key", "install", "needs"}      # keys, installs and the seats waiting on them: no option to pass


def test_the_critic_reports_a_link_the_sources_do_not_hold(tmp_path):
    def invented(method, url, **kwargs):
        return Reply({"organic": [{"title": "Rust", "link": "https://blog.rust-lang.org/", "snippet": "See https://example.org/made-up."}],
                      "answerBox": {"answer": "Read https://example.org/made-up and https://blog.rust-lang.org/"}})
    result = hubofhubs.run("hub-of-hubs", "Rust", **whole_hub(tmp_path, options={"search-backend": {"http": invented}}))
    assert "link not in the evidence" not in result.note      # both links are in the sources' text
    stranger = hubofhubs.run("think-critically", {"answer": "See https://other.example/x", "evidence": "https://blog.rust-lang.org/"})
    assert stranger == ["link not in the evidence: https://other.example/x"]


def test_the_model_alone_is_a_separate_call_that_says_it_has_no_sources(tmp_path):
    whole = hubofhubs.run(WholeAnswering, **whole_hub(tmp_path))
    result = whole.model_only("Reply with the single word: ok", "cheap")
    assert result.note.startswith("answered from the model only") and result.items == ()
    assert result.answer == "echo[claude-haiku-5-5]: Reply with the single word: ok" and result.seat == "reason-and-answer"


def test_one_function_at_every_level(tmp_path):
    store = hubofhubs.run(CardStore)                                  # a typed handle: its methods are known to an editor
    store.add(Card(id="a", text="Rust 1.90 is the release in these notes", source="notes", tags=("rust",)))
    assert [c.id for c in hubofhubs.run("card-store", "Rust release", provided={"card-store": store})] == ["a"]
    recalled = hubofhubs.run("remember-and-recall", "Rust release", provided={"card-store": store, "call-a-model": FakeProvider()}, environ={})
    assert [c.id for c in recalled] == ["a"]


def test_papers_run_the_scholarly_arm_on_a_recorded_response():
    body = json.loads((FIXTURES / "openalex_works_search.json").read_text(encoding="utf-8"))
    seen = []

    def transport(url, *, params, headers, timeout):
        seen.append(url)
        return Reply(body)
    observation = hubofhubs.run("know-the-world", "meditation and attention", arms={"know-the-world": "openalex"},
                                options={"know-the-world": {"transport": transport, "min_interval": 0}}, environ={})
    assert seen and observation.hits and observation.hits[0].get("title")


def test_every_hub_id_answers_or_names_what_to_set():
    """The strict definition behind the README's one function: with no environment each id returns a value or raises Pending."""
    import subprocess
    root = Path(__file__).resolve().parent.parent
    done = subprocess.run([sys.executable, "-m", "esoi.entry", "--json", str(root)], capture_output=True, text=True)
    rows = json.loads(done.stdout.strip().splitlines()[-1])      # the check blocks the network and programs for its own process, so it runs in one
    assert rows and {r["outcome"] for r in rows} <= {"ok", "pending-key", "pending-install"}, [r for r in rows if r["outcome"] not in ("ok", "pending-key", "pending-install")]


def test_needs_lists_the_lines_for_any_id():
    lines = hubofhubs.needs("take-in-the-world", environ={})
    assert any("GEMINI_API_KEY" in line for line in lines)
    assert hubofhubs.needs("search-backend", arms={"search-backend": "serper"}, environ={"SERPER_API_KEY": "k"}) == ()


def test_environ_defaults_to_the_process_environment(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    assert hubofhubs.needs("search-backend", arms={"search-backend": "serper"})
    monkeypatch.setenv("SERPER_API_KEY", "k")
    assert hubofhubs.needs("search-backend", arms={"search-backend": "serper"}) == ()
    assert hubofhubs.needs("search-backend", arms={"search-backend": "serper"}, environ={})   # an explicit mapping replaces it
    assert "search-backend" in hubofhubs.assemble(arms={"search-backend": "serper"})


def test_assemble_takes_no_required_argument_and_a_lock():
    assert "card-store" in hubofhubs.assemble()
    lock = {"schema": "esoi.lock/1", "solutions": {"card-store": {"arm": "local_card_store"}}}
    assert "card-store" in hubofhubs.assemble(lock=lock)


def test_the_cli_is_a_thin_wrapper(capsys):
    code = cli.main(["run", "latest Rust release", "--json"])
    assert code == 2 or code == 0   # 2 without a key in this environment
    out = capsys.readouterr()
    assert code == 2 and "GEMINI_API_KEY" in out.err or json.loads(out.out.strip().splitlines()[-1]).get("type") == "run"


def test_no_separate_ask():
    assert not hasattr(hubofhubs, "ask") and not hasattr(hubofhubs, "stream")


@pytest.mark.skipif(not os.environ.get("HUBOFHUBS_LIVE"), reason="live check: real search and model calls; not run by the suite")
def test_live_grounded_run_and_model_alone():
    """RUN LIVE on 2026-11-01 (passed, through the earlier question-first call): the Gemini key from the environment, the search arm
    gemini; the model through the Claude Code subscription (claude_cli, haiku), never the paid API. The whole hub answered
    "The latest stable release of Rust is version 1.99.1" with four sources, and the version matched the stable line of releases.rs."""
    grounded = hubofhubs.run("hub-of-hubs", "what is the latest Rust release?")
    assert grounded.answer and grounded.items and not grounded.note
    alone = hubofhubs.run(WholeAnswering).model_only("Reply with the single word: ok", "cheap")
    assert alone.answer and alone.note and alone.items == ()


def test_the_readme_blocks_run_as_written():
    """The first block pends on its key and the second runs offline as written: the README's one function, proven here."""
    import re
    from esoi import entry
    text = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    blocks = [b for b in re.findall(r"```pycon\n(.*?)```", text, flags=re.S) if "hubofhubs.run(" in b]
    first, second = entry.run_block(blocks[0], guard=False), entry.run_block(blocks[1], guard=False)
    assert not first["problems"] and not second["problems"] and not second["pending"], (first, second)
