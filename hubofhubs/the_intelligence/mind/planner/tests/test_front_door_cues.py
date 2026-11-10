"""What the planner sends where on a plain install: a question about the hub is answered from the hub, a named file is read, a lookup of several sentences is one search."""
import pytest

from hubofhubs.the_intelligence.mind.planner.planning import CueRouter


def tools(request):
    return [piece["tool"] for piece in CueRouter().plan(request)]


@pytest.mark.parametrize("text", ["What can you do?", "who are you", "How do you work?", "help", "Tell me about yourself"])
def test_a_question_about_the_hub_is_not_searched(text):
    assert tools(text) == ["role-understanding"]


def test_a_named_file_is_read_with_the_folder_and_the_file_in_the_request():
    plan = CueRouter().plan("What does notes.txt say about the budget?")
    assert plan[0]["tool"] == "read-files" and plan[0]["request"] == {"root": ".", "paths": ["notes.txt"]}


def test_an_edit_of_a_named_file_stays_an_edit():
    assert tools("Fix the bug in calc.py so add returns the sum") == ["file-editing"]


def test_a_version_number_or_a_site_is_not_a_file():
    assert tools("What is the latest stable version of Python 3.15?") == ["web-search"]
    assert tools("Who runs example.com?") == ["web-search"]


def test_sentences_of_one_lookup_are_one_search_and_numbered_steps_stay_separate():
    assert tools("Compare France and Germany, then say which has more people; then give the ratio?") == ["web-search"]
    assert len(tools("1. Look up the latest Python version\n2. Look up the latest Rust version")) == 2
