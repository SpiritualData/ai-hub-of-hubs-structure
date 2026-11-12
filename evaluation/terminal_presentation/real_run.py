"""A run shaped like the real native harness's, replayed: the event stream a real one-line run emitted (recorded 2026-11-11 on a real fast-tier session, anonymised: a neutral goal, no ids, no
paths; ``real_native_run.json``). What the scripted ``pasted_run`` did not have and a real run does: the interim note is the answer cut at about a hundred characters with three dots and its
markdown, and three ``Usage`` events come between that note and the ``Finished`` (so an arm that dropped the held note only when the very next event was the ``Finished`` showed the answer twice).
Standard library only."""
import json
import time
from pathlib import Path
from typing import Callable

from hubofhubs.the_consciousness.ai_session_experience.session_events import Capabilities, event_from_dict

EVENTS = json.loads((Path(__file__).resolve().parent / "real_native_run.json").read_text())
GOAL = "What is today?"


class RealRun:
    """A ``Harness`` that replays the recorded events and takes no control."""
    name = "native"
    capabilities = Capabilities(stop=False, resume=False, steer=False)

    def __init__(self, pause: float = 0.12) -> None:
        self.pause = pause

    def start(self, goal: str, sink: Callable, resume_session_id: str = ""):
        done = None
        for item in EVENTS:
            event = event_from_dict(item)
            sink(event)
            if event.type == "finished":
                done = event
            time.sleep(self.pause)
        return done

    def control(self, control) -> bool:
        return False


class Kit:
    goal = GOAL

    def __init__(self) -> None:
        self.harness = RealRun()
