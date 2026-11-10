"""Rebuild cases.json for Terminal Session: invented scripted-stdin sessions against a stub front door. The expected result is written by hand from what a
person typing those lines should see, never produced by an arm.

Kinds of case (case sources of one component, reported separately):
  turn     a typed line reaches the front door and its answer and interim update are shown.
  command  /help, /trail and an unknown command are answered by the session and never reach the front door.
  ask      a question the hub asks is shown with its options and the next line answers it (a number picks an option).
  attend   a person works with a run while it works (watch, stop, resume, steer, tree, approve, refuse, target, frame, and the hub's own parts: structure toggle and
           expand, ceilings, soft limit, stop decision, end of run, follow-up, harness switch, no-goal prompt, representative), scripted on two harnesses.
  exit     /quit, end of input and a front door that cannot start all end the session cleanly.

    python3 evaluation/terminal_session/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def case(name, kind, rule, lines, replies, expect_calls, must_show, setup_error=False):
    return {"id": "session-" + name, "kind": kind, "origin": "rule: " + rule,
            "args": {"lines": lines, "replies": replies, "must_show": must_show, "setup_error": setup_error},
            "expect": {"door_calls": expect_calls, "missing": [], "exit_code": 0, "ended": True}}


def reply(answer="", interim="", ask=None):
    events = []
    if interim:
        events.append({"type": "interim", "text": interim, "data": {}})
    if ask:
        events.append({"type": "decision", "text": "", "data": ask})
    return {"answer": answer, "events": events}


CASES = [
    case("one-turn", "turn", "a line is run once and its answer shown", ["hello\n", "/quit\n"], {"hello": reply("Hi there.")}, ["hello"], ["Hi there."]),
    case("two-turns-in-order", "turn", "two lines reach the front door in the order typed", ["first\n", "second\n", "/quit\n"],
         {"first": reply("One."), "second": reply("Two.")}, ["first", "second"], ["One.", "Two."]),
    case("interim-shown", "turn", "an interim update of the run is shown", ["go\n", "/quit\n"], {"go": reply("Done.", interim="Reading the notes")},
         ["go"], ["Reading the notes", "Done."]),
    case("blank-lines-skipped", "turn", "a blank line runs nothing", ["\n", "  \n", "hi\n", "/quit\n"], {"hi": reply("Hello.")}, ["hi"], ["Hello."]),
    case("help-lists-commands", "command", "/help names the commands and runs nothing", ["/help\n", "/quit\n"], {}, [], ["/trail", "/quit", "/help"]),
    case("trail-toggles", "command", "/trail says whether the trail is on", ["/trail\n", "/trail\n", "/quit\n"], {}, [], ["Trail on.", "Trail off."]),
    case("unknown-command", "command", "an unknown command is named and runs nothing", ["/nope\n", "/quit\n"], {}, [], ["Unknown command /nope"]),
    case("ask-number-picks-option", "ask", "a number answers an open question with that option",
         ["find it\n", "2\n", "/quit\n"],
         {"find it": reply("Need a choice.", ask={"decision_id": "d1", "question": "Which source?", "options": ["Web", "Library"]}), "Library": reply("Used the library.")},
         ["find it", "Library"], ["Which source?", "1. Web", "Used the library."]),
    case("ask-free-text", "ask", "any other text answers an open question as typed",
         ["plan\n", "the second draft\n", "/quit\n"],
         {"plan": reply("Which draft?", ask={"decision_id": "d2", "question": "Which draft?"}), "the second draft": reply("Using it.")},
         ["plan", "the second draft"], ["Which draft?", "Using it."]),
    case("ask-folded-by-later", "ask", "/later folds a question without answering it, and the next line is a new message",
         ["plan\n", "/later\n", "other\n", "/quit\n"],
         {"plan": reply("Which draft?", ask={"decision_id": "d3", "question": "Which draft?"}), "other": reply("Fine.")},
         ["plan", "other"], ["Which draft?", "Fine."]),
    case("quit-stops-reading", "exit", "/quit ends the session before later lines", ["/quit\n", "never\n"], {"never": reply("No.")}, [], ["Goodbye."]),
    case("end-of-input", "exit", "end of input ends the session cleanly", ["hi\n"], {"hi": reply("Hello.")}, ["hi"], ["Hello.", "Goodbye."]),
    case("empty-input", "exit", "no input at all ends the session cleanly", [], {}, [], ["Goodbye."]),
    case("setup-needed", "exit", "a front door that cannot start shows what to set and the session goes on", ["hi\n", "/quit\n"], {}, ["hi"],
         ["needs setup", "Goodbye."], setup_error=True),
]

REQUIREMENTS = {
    "watch": ["X1", "X2", "X3", "X10", "X16"], "stop_resume": ["X4", "X5", "X21"], "steer": ["X6", "X23"], "tree": ["X7"], "solution_tree": ["X15"],
    "approve": ["X9", "X19", "X22"], "refuse": ["X9", "X20"], "target": ["X8"], "same_surface": ["X11", "X12"], "plain_and_replay": ["X13", "X18"],
    "frame": ["X14", "X17"], "live_helper": ["X7"], "stop_prompt": ["X4", "X5"], "solution_agents": ["X14", "X15"],
    "check_never_passes": ["X10", "X20"], "repeat_refused": ["X20"],
    "structure_toggle": ["X24", "X18"], "structure_expand": ["X25", "X18"], "ceiling_status": ["X26", "X3"], "soft_limit_line": ["X27"], "stop_decision_line": ["X28"],
    "end_of_run": ["X21", "X33"], "follow_up_continues": ["X29", "X5"], "harness_switch": ["X30", "X11"], "no_goal_prompt": ["X31"], "representative": ["X32"],
}
SESSIONS = [("watch", "loop"), ("watch", "stream"), ("stop_resume", "loop"), ("stop_resume", "stream"), ("steer", "loop"), ("steer", "stream"),
            ("tree", "loop"), ("tree", "stream"), ("solution_tree", "none"), ("approve", "loop"), ("approve", "stream"), ("refuse", "loop"), ("refuse", "stream"),
            ("target", "loop"), ("target", "stream"), ("same_surface", "both"), ("plain_and_replay", "loop"), ("plain_and_replay", "stream"),
            ("frame", "loop"), ("frame", "stream"), ("live_helper", "loop"), ("stop_prompt", "loop"), ("solution_agents", "solutions"), ("check_never_passes", "loop"), ("repeat_refused", "loop"),
            ("structure_toggle", "stream"), ("structure_expand", "stream"), ("ceiling_status", "stream"), ("soft_limit_line", "stream"), ("stop_decision_line", "stream"),
            ("end_of_run", "stream"), ("follow_up_continues", "stream"), ("harness_switch", "both"), ("no_goal_prompt", "stream"), ("representative", "stream")]
for scenario, kit in SESSIONS:
    CASES.append({"id": f"attend-{scenario}-{kit}", "kind": "attend", "origin": "rule: " + scenario.replace("_", " ") + f" on the {kit} harness (docs/explanation/working-with-the-ai-while-it-works.md)",
                  "args": {"scenario": scenario, "kit": kit}, "requirements": REQUIREMENTS[scenario], "expect": {"failed": []}})

if __name__ == "__main__":
    (HERE / "cases.json").write_text(json.dumps(CASES, indent=1) + "\n")
    print(len(CASES), "cases")
