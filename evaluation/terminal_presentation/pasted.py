"""The run the owner pasted (2026-11-11, a narrow terminal, a one-question run), as scripted events: no model, no network. It has what the owner saw go wrong: the goal as a question,
the harness's lifecycle note, a command step, an interim note that is the beginning of the answer, markdown in the answer, a cost with four decimals, ceilings far from used, and a
session id long enough that a resume command wraps on a narrow screen. The harness takes a short pause between events so a screen can be read while it works."""
import time
from typing import Callable

from hubofhubs.the_consciousness.ai_session_experience.session_events import Capabilities, Finished, RunStarted, Step, Usage

SESSION = "0a239607-4796-46d9-a544-6eebe0537683"
GOAL = "What is today?"
ANSWER = ("Today is **Wednesday, November 11, 2026**. The system clock read 6:43 PM PST when I checked.\n\n"
          "I checked it with the `date` command and didn't change any files.")
NOTE = "Today is **Wednesday, November 11, 2026**. The system clock read 6:..."
PAUSE = 0.12


class PastedRun:
    """A ``Harness`` that plays the pasted run and takes no control."""
    name = "native"
    capabilities = Capabilities(stop=False, resume=False, steer=False)

    def __init__(self, pause: float = PAUSE) -> None:
        self.pause = pause

    def start(self, goal: str, sink: Callable, resume_session_id: str = "") -> Finished:
        def send(event):
            sink(event)
            time.sleep(self.pause)
        send(RunStarted(at=0.0, goal=goal or GOAL, harness="native", session_id=SESSION))
        send(Step(at=0.5, step_id="s0", kind="note", label="session started", state="done"))
        send(Step(at=3.0, step_id="s1", kind="run", label="date", state="running"))
        send(Step(at=3.1, step_id="s1", kind="run", label="date", state="done"))
        send(Usage(at=3.5, cost_usd=0.2077, tokens=135, calls=2, ceiling_usd=20.0, ceiling_seconds=14400.0))
        send(Step(at=4.0, step_id="s2", kind="note", label=NOTE, state="done"))
        done = Finished(at=5.0, outcome="met", report=ANSWER, session_id=SESSION, cost_usd=0.2077, tokens=135, spend_usd=0.2077, elapsed_seconds=5.0)
        sink(done)
        return done

    def control(self, control) -> bool:
        return False


class Kit:
    goal = GOAL

    def __init__(self) -> None:
        self.harness = PastedRun()
