"""The line REPL, driven by scripted input and a stub front door."""
import io
from dataclasses import dataclass
from typing import Tuple

from hubofhubs.the_consciousness.terminal.repl import LineRepl
from hubofhubs.the_world.tools.deep import ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_DECISION, EVENT_INTERIM


@dataclass
class Reply:
    answer: str = ""
    events: Tuple[ProgressEvent, ...] = ()
    note: str = ""


def run(lines, front_door):
    out = io.StringIO()
    code = LineRepl().converse(front_door, io.StringIO(lines), out)
    return code, out.getvalue()


def test_a_normal_turn_draws_interim_and_answer():
    seen = []

    def door(text):
        seen.append(text)
        return Reply("Four.", (ProgressEvent(type=EVENT_INTERIM, text="Adding the numbers", data={}),))

    code, shown = run("what is 2+2\n/quit\n", door)
    assert code == 0 and seen == ["what is 2+2"]
    assert "Adding the numbers" in shown and "Four." in shown and shown.rstrip().endswith("Goodbye.")


def test_help_and_unknown_commands_do_not_reach_the_front_door():
    seen = []
    code, shown = run("/help\n/nope\n/trail\n/quit\n", lambda text: seen.append(text))
    assert not seen and "/quit" in shown and "Unknown command /nope" in shown and "Trail on." in shown


def test_quit_stops_reading():
    seen = []
    run("/quit\nhello\n", lambda text: seen.append(text) or Reply("x"))
    assert not seen


def test_an_ask_is_drawn_and_the_next_line_answers_it():
    seen = []
    ask = ProgressEvent(type=EVENT_DECISION, text="", data={"decision_id": "d1", "question": "Which source?", "options": ["Web", "Library"]})

    def door(text):
        seen.append(text)
        return Reply("Need a choice.", (ask,)) if len(seen) == 1 else Reply("Used it.")

    code, shown = run("find it\n2\n", door)
    assert seen == ["find it", "Library"]
    assert "Which source?" in shown and "1. Web" in shown and "Used it." in shown


def test_end_of_input_exits_cleanly():
    code, shown = run("", lambda text: Reply("x"))
    assert code == 0 and shown.rstrip().endswith("Goodbye.")


def test_a_run_that_cannot_start_shows_what_to_set():
    from esoi import Pending

    def door(text):
        raise Pending("hub-of-hubs", ["set SOME_KEY"])

    code, shown = run("hi\n", door)
    assert code == 0 and "needs setup" in shown
