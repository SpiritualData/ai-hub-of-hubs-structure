"""Rebuild cases.json for Frontend Interface: does each event and control of a session reach a frontend as plain data, with the run facts, and nothing of a terminal?

The events and the expected values are written by hand from the contract (hubofhubs/the_consciousness/ai_session_experience/session_events.py), never produced by
an arm. Kinds of case (case sources of one component, reported separately):
  event    each of the eight event kinds goes to JSON and back to an equal event.
  control  each of the five control kinds does.
  facts    cost, helpers with parent and solution, changed files, a steer sent then taken up, the open question, the outcome.
  leak     no escape code, key hint or terminal wording is in the data.
  unknown  an event of a type nobody knows is kept apart and the rest of the picture is still made.

    python3 evaluation/frontend_interface/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

EVENTS = {
    "run-started": {"type": "run-started", "at": 0.0, "agent_id": "main", "goal": "fix the parser", "harness": "loop", "session_id": "s1", "resumed": False,
                    "solution": "the-mind", "milestone": "1. plan", "frame": "approach", "metric": "metric-the-mind", "metric_before": 0.5},
    "step": {"type": "step", "at": 1.0, "agent_id": "main", "step_id": "t1", "kind": "edit", "label": "app.py", "state": "done", "detail": ""},
    "agent-started": {"type": "agent-started", "at": 2.0, "agent_id": "h1", "parent_id": "main", "task": "write tests", "solution": "planner"},
    "agent-ended": {"type": "agent-ended", "at": 3.0, "agent_id": "h1", "state": "met", "calls": 3, "summary": "done"},
    "review": {"type": "review", "at": 4.0, "agent_id": "main", "text": "no change", "corrections": 0},
    "waiting": {"type": "waiting", "at": 5.0, "agent_id": "main", "ask_id": "a1", "question": "Deploy it?", "risky": "deploy", "preview": "the site changes",
                "options": ["approve", "refuse"]},
    "usage": {"type": "usage", "at": 6.0, "agent_id": "main", "cost_usd": 0.42, "tokens": 1200, "calls": 5, "cache_read_tokens": 100, "cache_write_tokens": 20},
    "finished": {"type": "finished", "at": 7.0, "agent_id": "main", "outcome": "met", "report": "All done.", "changed": ["app.py"], "session_id": "s1", "error": "",
                 "cost_usd": 0.5, "tokens": 1500, "unseen": [], "metric_after": 0.8, "blocked": []},
}
CONTROLS = {
    "stop": {"type": "stop", "agent_id": ""},
    "resume": {"type": "resume", "agent_id": ""},
    "steer": {"type": "steer", "agent_id": "h1", "text": "use the other file", "message_id": "m1"},
    "approve": {"type": "approve", "agent_id": "", "ask_id": "a1"},
    "refuse": {"type": "refuse", "agent_id": "", "ask_id": "a1", "reason": "not now"},
}


def case(name, kind, rule, args, expect):
    return {"id": "frontend-" + name, "kind": kind, "origin": "rule: " + rule, "args": args, "expect": expect}


CASES = []
for name, data in EVENTS.items():
    CASES.append(case("event-" + name, "event", f"a {name} event goes to JSON and back equal", {"check": "event", "data": data}, {"round_trip": True, "plain": True}))
for name, data in CONTROLS.items():
    CASES.append(case("control-" + name, "control", f"a {name} control goes to JSON and back equal", {"check": "control", "data": data}, {"round_trip": True, "plain": True}))

RUN = [EVENTS["run-started"], dict(EVENTS["step"], step_id="t1"), dict(EVENTS["step"], step_id="t2", label="b.py", state="failed"),
       EVENTS["agent-started"], dict(EVENTS["agent-ended"], calls=3), EVENTS["usage"]]


def facts(name, rule, events, controls, paths, expect):
    CASES.append(case("facts-" + name, "facts", rule, {"check": "facts", "events": events, "controls": controls, "paths": paths}, dict(zip(paths, expect))))


facts("cost", "the cost, tokens and calls so far are in the picture", RUN, [], ["cost.usd", "cost.tokens", "cost.calls", "cost.cache_read_tokens"], [0.42, 1200, 5, 100])
facts("helpers", "a helper has its parent, task, solution, state and calls", RUN, [], ["helpers.0.agent_id", "helpers.0.parent_id", "helpers.0.solution", "helpers.0.state", "helpers.0.calls"],
      ["h1", "main", "planner", "met", 3])
facts("changed-files", "an edit that failed is not a changed file", RUN, [], ["changed"], [["app.py"]])
facts("serves", "what the work serves and the metric before are in the picture", RUN, [], ["serves.solution", "serves.milestone", "serves.metric_before", "status"],
      ["the-mind", "1. plan", 0.5, "running"])
facts("steer-sent", "a message sent is listed and not taken up yet", RUN, [CONTROLS["steer"]], ["messages.0.text", "messages.0.taken_up", "messages.0.agent_id"],
      ["use the other file", False, "h1"])
facts("steer-taken-up", "a message the harness says it took up is marked taken up", RUN + [{"type": "step", "agent_id": "main", "step_id": "m1", "kind": "message-received", "label": "use the other file", "state": "done"}],
      [CONTROLS["steer"]], ["messages.0.taken_up"], [True])
facts("pending-question", "an open question is the pending input with its preview and options", RUN + [EVENTS["waiting"]], [],
      ["status", "pending_input.question", "pending_input.preview", "pending_input.options"], ["waiting", "Deploy it?", "the site changes", ["approve", "refuse"]])
facts("question-closes", "the next step closes the pending input", RUN + [EVENTS["waiting"], dict(EVENTS["step"], step_id="t3", label="c.py")], [], ["status", "pending_input"], ["running", None])
facts("outcome", "the outcome, report, files and metric after are in the picture", RUN + [EVENTS["finished"]], [],
      ["status", "outcome", "report", "changed", "serves.metric_after", "cost.usd"], ["finished", "met", "All done.", ["app.py"], 0.8, 0.5])
facts("blocked-and-unseen", "what was blocked and the messages never taken up are listed",
      [EVENTS["run-started"], dict(EVENTS["finished"], outcome="stopped", blocked=["deploy: refused"], unseen=["one more thing"], changed=[])], [], ["status", "blocked", "unseen"],
      ["stopped", ["deploy: refused"], ["one more thing"]])
facts("replay-same", "the same events give the same picture twice", RUN, [], ["steps.0.label", "steps.1.state"], ["app.py", "failed"])

for name, events in (("whole-run", RUN + [EVENTS["waiting"], EVENTS["finished"]]), ("empty", [])):
    CASES.append(case("leak-" + name, "leak", "the picture names nothing of a terminal and is plain JSON", {"check": "leak", "events": events, "controls": [CONTROLS["steer"]]},
                      {"leaks": [], "plain": True}))
CASES.append(case("unknown-event", "unknown", "an event of an unknown type is kept apart and the picture is still made",
                  {"check": "facts", "events": [EVENTS["run-started"], {"type": "hologram", "at": 1}, EVENTS["usage"]], "controls": [], "paths": ["goal", "cost.usd", "unknown_events.0.type"]},
                  {"goal": "fix the parser", "cost.usd": 0.42, "unknown_events.0.type": "hologram"}))
CASES.append(case("unknown-control", "unknown", "a control of an unknown type is left out and the picture is still made",
                  {"check": "facts", "events": [EVENTS["run-started"]], "controls": [{"type": "teleport"}, CONTROLS["steer"]], "paths": ["goal", "messages.0.text"]},
                  {"goal": "fix the parser", "messages.0.text": "use the other file"}))

if __name__ == "__main__":
    (HERE / "cases.json").write_text(json.dumps(CASES, indent=1) + "\n")
    print(len(CASES), "cases")
