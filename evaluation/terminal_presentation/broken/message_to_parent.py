"""A deliberately broken arm (revision 4): the reference terminal whose message typed inside a helper goes to that helper's parent (the main session for a helper at the first level), so the
screen shows the message but the wrong agent receives it. The message check must catch it."""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.session_events import MAIN, Steer  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession  # noqa: E402


class ToParent:
    """The harness as the arm sees it, with each message to a helper re-aimed at the helper's parent."""

    def __init__(self, inner):
        self.inner = inner
        self.name, self.capabilities = inner.name, inner.capabilities
        self.parents = {}

    def start(self, goal, sink, resume_session_id=""):
        def seen(event):
            if event.type == "agent-started":
                self.parents[event.agent_id] = event.parent_id
            sink(event)
        return self.inner.start(goal, seen, resume_session_id)

    def control(self, control):
        if isinstance(control, Steer) and control.agent_id:
            parent = self.parents.get(control.agent_id, MAIN)
            control = replace(control, agent_id="" if parent == MAIN else parent)
        return self.inner.control(control)


class MessageToParent(LiveSession):
    def attend(self, harness, goal, out, keys=None, *args, **kwargs):
        return super().attend(ToParent(harness), goal, out, keys, *args, **kwargs)


def build(meter):
    return score.adapt(MessageToParent, meter)
