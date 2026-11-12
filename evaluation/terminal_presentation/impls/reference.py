"""The reference arm of the presentation metric: the reference terminal (``live_session``) drawn by its own code. Any other arm is measured by name (``--impl live_session``,
``--impl textual_session``) and found through the records; this wrapper is the arm the broken baselines are compared with."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession  # noqa: E402


def build(meter):
    return score.adapt(LiveSession, meter)
