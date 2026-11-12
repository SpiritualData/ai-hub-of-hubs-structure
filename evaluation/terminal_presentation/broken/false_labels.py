"""A deliberately broken arm: the reference terminal that DECLARES words its screen never shows (an allow label, a refuse label, a stop hint and a marker for the person's message that the
reference does not draw). The checks that read the fact through declared labels must fail it: a declared label that is not on the screen is a false declaration, never a pass."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession  # noqa: E402


class FalseLabels(LiveSession):
    screen_labels = {"allow": "Allow once please", "refuse": "Decline it", "stop": "ctrl+x halts", "person": "»»"}


def build(meter):
    return score.adapt(FalseLabels, meter)
