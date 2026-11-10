"""One request, offline, with no key: Body's declared source feeds the Subconscious through Internal Context, the Context Retriever runs on what Body
returns, the Mind answers from that view, and the run record goes to the run store and never into the cards recall searches."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs  # noqa: E402


def walk(steps):
    for step in steps:
        yield step
        yield from walk(step.get("steps", ()))


def build(tmp_path):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "cats.md").write_text("# Cats\n\nCats sleep for most of the day and wake at dusk.\n", encoding="utf-8")
    (folder / "bees.md").write_text("# Bees\n\nBees dance to tell the hive where the flowers are.\n", encoding="utf-8")
    return hubofhubs.assemble(options={"internal-context": {"root": str(folder)}}, environ={})


def test_a_request_flows_from_body_through_the_subconscious_to_the_mind_with_the_retriever_running(tmp_path):
    system = build(tmp_path)
    result = system["the-self"].respond("Explain how cats spend the day")
    every = {s["solution"]: s for s in walk(result.steps) if s["solution"] in ("context-retriever", "context-intake", "planner", "delegation", "response-writer")}
    assert every["context-retriever"]["status"] == "done"            # the retriever ran on what Internal Context returned, not on nothing
    assert "Cats sleep for most of the day" in result.answer          # the Mind's view held the file Body declared, and the writer wrote from it
    assert result.note == ""


def test_the_request_reaches_the_subconscious_only_through_internal_context(tmp_path):
    system = build(tmp_path)
    internal = system["internal-context"]
    assert any(name.endswith("cats.md") for name in internal.corpus())
    assert internal.declared()[0]["where"] == str(tmp_path / "notes") and internal.declared()[0]["tool"] == "read-files"
    prepared = system["the-subconscious"].prepare("Explain how cats spend the day")
    assert any(getattr(piece, "file", "").endswith("cats.md") for piece in prepared["pieces"])


def test_the_run_record_is_kept_in_the_run_store_and_recall_never_returns_it(tmp_path):
    system = build(tmp_path)
    system["the-self"].respond("Explain how cats spend the day")
    internal = system["internal-context"]
    runs = internal.runs_so_far()
    assert len(runs) == 1 and runs[0]["request"] == "Explain how cats spend the day" and runs[0]["sources"][0]["where"] == str(tmp_path / "notes")
    assert internal.read("Explain how cats spend the day", limit=10) == []                 # no card was made for the run
    assert [card for card in system["the-subconscious"].recall("Explain how cats spend the day")] == []


def test_a_request_with_nothing_known_says_so_and_is_not_met(tmp_path):
    empty = hubofhubs.assemble(environ={})
    result = empty["the-self"].respond("Explain how cats spend the day")
    assert "could not answer" in result.answer and "To enable it" in result.answer and result.stopped == "unavailable"      # nothing known, no search here: said plainly, not a budget stop
    assert result.note == ""
    assert next(s for s in walk(result.steps) if s["solution"] == "context-retriever")["status"] == "skipped"
