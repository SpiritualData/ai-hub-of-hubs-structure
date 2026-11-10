"""The hub works on a plain install: only a logged-in Claude CLI, no vendor key, no extra library chosen. The front door runs with an empty environment mapping holding a PATH with the
one program (a replay of the CLI's JSON reply envelope is the only thing faked), and no ordinary input ends in an unhandled error, a raw error line or a warning.

The cases are the ones the evaluation component ``plain_install`` scores (``evaluation/plain_install/build_cases.py``); a supporting step that cannot run never fails the answer."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs  # noqa: E402
from evaluation.plain_install import fake_claude  # noqa: E402
from evaluation.plain_install.score import RAW, score_case  # noqa: E402

CASES = json.loads((Path(__file__).resolve().parent.parent / "evaluation" / "plain_install" / "cases.json").read_text())


@pytest.fixture
def door(tmp_path, monkeypatch):
    """``ask(text, files)``: the front door run in a folder holding ``files`` with only the stand-in program on the PATH; ``ask.calls()`` counts the model calls made."""
    bindir = fake_claude.install(tmp_path / "bin")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv("PATH", str(bindir))

    def ask(text, files=None, path=None):
        for name, body in (files or {}).items():
            (work / name).write_text(body)
        return hubofhubs.run("the-self", {"request": text, "person": ""}, environ={"PATH": str(bindir) if path is None else path})

    ask.calls = lambda: len((bindir / "claude.calls").read_text().splitlines()) if (bindir / "claude.calls").is_file() else 0
    return ask


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_no_ordinary_input_ends_in_an_error_or_a_warning(door, case):
    result = door(case["args"]["request"], case["args"]["files"])
    assert isinstance(result, hubofhubs.Result) and result.answer.strip()
    assert not [w for w in RAW if w in result.answer], result.answer[:200]
    assert result.note == "", f"a warning on a plain install: {result.note}"
    held = [w.lower() in result.answer.lower() for w in case["expect"]["contains"]]
    assert any(held) if case["expect"].get("any") else all(held), result.answer[:200]


def test_the_scoring_of_the_component_passes_every_case_through_the_same_door(door):
    for case in CASES:
        got = door(case["args"]["request"], case["args"]["files"])
        row = score_case(lambda kind, args, got=got: {"answer": got.answer, "note": got.note, "steps": [], "broken": []}, case)
        assert row["ok"], (case["id"], row["note"])


def test_a_question_about_the_hub_is_answered_from_its_records_with_no_search_and_no_model_call(door):
    result = door("What can you do?")
    assert "hub of hubs" in result.answer and "Intelligence" in result.answer
    assert door.calls() == 0
    assert result.stopped == ""


def test_a_question_that_needs_the_web_is_searched_through_the_login_when_no_search_key_is_set(door):
    result = door("What is the latest stable version of Python?")
    assert "3.15" in result.answer and door.calls() == 1
    stood = {row["solution"]: row["arm"] for row in result.stood_in}
    assert stood.get("web-search") == "claude_login" and "vendor-model-caller" in stood      # the detail is kept, and is not a message
    assert result.note == ""


def test_a_local_file_is_read_there_and_not_searched_for(door):
    result = door("What does notes.txt say about the budget?", {"notes.txt": "Budget: 12000 dollars\n"})
    assert "12000" in result.answer and door.calls() == 0


def test_a_change_to_a_file_says_how_to_allow_it_and_is_not_a_budget_stop(door):
    result = door("Fix the bug in calc.py so add returns the sum", {"calc.py": "def add(a, b):\n    return a - b\n"})
    assert "ahohs work" in result.answer and result.stopped == "asked" and "budget" not in result.answer + result.note
    assert (Path("calc.py").read_text()) == "def add(a, b):\n    return a - b\n"


def test_when_no_search_can_run_the_answer_says_so_in_plain_words_and_how_to_enable_one(door):
    result = door("What is the latest stable version of Python?", path="")
    assert result.stopped == "unavailable" and "could not answer" in result.answer and "To enable it" in result.answer
    assert not [w for w in RAW if w in result.answer + result.note] and "budget" not in result.answer + result.note


def test_a_needed_step_that_breaks_is_a_message_never_a_traceback(door, monkeypatch):
    arm = hubofhubs.resolve("the-self")

    def broken(*args, **kwargs):
        raise RuntimeError("the intelligence could not start")
    monkeypatch.setitem(arm.respond.__globals__, "take", broken)      # the module the hub itself loaded
    result = door("What can you do?")
    assert result.stopped == "unavailable" and "could not finish" in result.answer and "Traceback" not in result.answer
