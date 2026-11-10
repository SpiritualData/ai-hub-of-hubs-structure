"""Tests of the AI Session Experience composition: one session gives the structure, the frontend data and the terminal lines."""
import io

from hubofhubs.the_consciousness.ai_session_experience.flow import AiSessionExperienceComposition
from hubofhubs.the_consciousness.ai_session_experience.frontend_interface.wire import JsonWire
from hubofhubs.the_consciousness.ai_session_experience.interface import SessionExperiencing
from hubofhubs.the_consciousness.ai_session_experience.structure_in_view.tree import EventTree
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.repl import LineRepl


EVENTS = [{"type": "run-started", "goal": "g", "solution": "the-mind"},
          {"type": "agent-started", "agent_id": "the-mind-planner", "parent_id": "main", "task": "Planner", "solution": "planner"}]


def test_one_session_gives_three_views():
    arm = AiSessionExperienceComposition(LineRepl(), JsonWire(), EventTree())
    assert isinstance(arm, SessionExperiencing)
    out = arm.present(EVENTS)
    assert [n["solution"] for n in out["structure"]["tree"]] == ["the-mind"] and out["frontend"]["helpers"][0]["solution"] == "planner"
    assert out["terminal"][0].startswith("  the-mind") or "the-mind" in out["terminal"][0]
    assert [s["status"] for s in out["steps"]] == ["done", "done", "done"]


def test_converse_goes_to_the_terminal():
    out = io.StringIO()
    code = AiSessionExperienceComposition(LineRepl(), JsonWire(), EventTree()).converse(lambda text: "heard", ["/quit\n"], out)
    assert code == 0
