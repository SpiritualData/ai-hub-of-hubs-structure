"""Tests of the Structure In View arm: the tree of solutions, collapsed by default and opened on request, from invented records and from the events of the solution workers."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "evaluation" / "structure_in_view"))

import fixture  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.structure_in_view.interface import StructureViewing  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.structure_in_view.tree import EventTree, structure_view  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.structure_lines import structure_lines  # noqa: E402
from hubofhubs.the_intelligence.mind.delegation.solution_workers import work_solution  # noqa: E402


def test_the_arm_satisfies_the_interface():
    assert isinstance(EventTree(), StructureViewing)


def test_collapsed_by_default_and_opened_on_request():
    closed = structure_view(fixture.SESSION, fixture.TABLES)
    assert "detail" not in json.dumps(closed) and not any(t in json.dumps(closed) for t in fixture.FIELD_TEXTS)
    opened = structure_view(fixture.SESSION, fixture.TABLES, ["root-sol"])
    assert opened["tree"][0]["detail"]["fields"]["purpose"] == "Root purpose text." and opened["expanded"] == ["root-sol"]


def test_the_events_of_the_solution_workers_make_the_right_tree():
    events = []
    delegates = {"root-sol": ["child-a", "child-b"], "child-a": [], "child-b": []}
    work_solution("root-sol", frame=lambda sid: {"name": sid.upper(), "milestone": "m"}, children=lambda sid, task="": delegates[sid], work=lambda brief: "out",
                  check=lambda sid, milestone, output: {"met": True}, task="t", session=events.append, budget={"calls": 8})
    view = structure_view([{"type": "run-started", "goal": "t", "solution": "root-sol"}] + events)
    root = view["tree"][0]
    assert root["solution"] == "root-sol" and [c["solution"] for c in root["children"]] == ["child-a", "child-b"]
    assert [a["agent_id"] for a in root["children"][0]["agents"]] == ["root-sol-child-a"] and root["state"] == "running"


def test_terminal_lines_are_one_per_solution_until_opened():
    closed = structure_lines(structure_view(fixture.SESSION, fixture.TABLES))
    assert len(closed) == 5 and closed[0].startswith("+ Root Solution (root-sol)") and not any("purpose:" in line for line in closed)
    opened = structure_lines(structure_view(fixture.SESSION, fixture.TABLES, ["root-sol"]))
    assert any(line.strip().startswith("purpose: Root purpose text.") for line in opened) and any("metric: Root Metric: 0.91" in line for line in opened)


def test_records_that_cannot_be_read_do_not_break_the_view():
    view = structure_view(fixture.SESSION, "/nonexistent-records-root", ["*"])
    assert view["unknown"] and all(n["detail"]["known"] is False for n in view["tree"])
