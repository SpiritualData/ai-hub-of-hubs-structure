"""Tests of the Frontend Interface arm: every event and control round-trips through JSON and the picture of a run is plain data."""
import json

from hubofhubs.the_consciousness.ai_session_experience.frontend_interface.interface import FrontendInterfacing
from hubofhubs.the_consciousness.ai_session_experience.frontend_interface.wire import JsonWire
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Approve, Finished, Refuse, Resume, Review, RunStarted, Step, Steer, Stop, Usage, Waiting)


def test_the_arm_satisfies_the_interface():
    assert isinstance(JsonWire(), FrontendInterfacing)


def test_every_event_and_control_round_trips_through_json():
    wire = JsonWire()
    for event in (RunStarted(goal="g", solution="s"), Step(step_id="1", label="a.py", kind="edit"), AgentStarted(agent_id="h", solution="s"), AgentEnded(agent_id="h"),
                  Review(text="ok"), Waiting(ask_id="a", question="q"), Usage(cost_usd=0.1), Finished(outcome="met", changed=("a.py",))):
        assert wire.decode_event(json.loads(json.dumps(wire.encode_event(event)))) == event
    for control in (Stop(), Resume(), Steer(text="x", message_id="m"), Approve(ask_id="a"), Refuse(ask_id="a", reason="no")):
        assert wire.decode_control(json.loads(json.dumps(wire.encode_control(control)))) == control


def test_the_picture_has_the_run_facts_as_plain_json():
    events = [RunStarted(goal="g", solution="s"), AgentStarted(agent_id="h", parent_id="main", solution="p", task="t"), Step(step_id="1", kind="edit", label="a.py"),
              Usage(cost_usd=0.2, tokens=10, calls=2), Waiting(ask_id="a", question="deploy?", preview="the site")]
    picture = JsonWire().snapshot(events, [Steer(text="hi", message_id="m1")])
    assert json.loads(json.dumps(picture)) == picture
    assert picture["status"] == "waiting" and picture["cost"]["usd"] == 0.2 and picture["changed"] == ["a.py"] and picture["helpers"][0]["solution"] == "p"
    assert picture["pending_input"]["question"] == "deploy?" and picture["messages"][0]["taken_up"] is False
