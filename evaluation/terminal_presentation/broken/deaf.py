"""A deliberately broken arm: the reference terminal that draws the run but reads no key, so a stop, a steer and an answer reach nothing. The presentation metric must catch it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession  # noqa: E402


class Deaf(LiveSession):
    def attend(self, harness, goal, out, keys=None, *args, **kwargs):
        return super().attend(harness, goal, out, None, *args, **kwargs)


def build(meter):
    return score.adapt(Deaf, meter)
