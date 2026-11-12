"""A deliberately broken arm: the reference terminal that never erases its previous frame before drawing the next, so every frame is stacked under the last (the screen shows
the same update many times). The presentation metric must catch it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import live  # noqa: E402


class NoErase(live.LiveSession):
    def attend(self, *args, **kwargs):
        keep = live.Painter.erase
        live.Painter.erase = lambda painter: None
        try:
            return super().attend(*args, **kwargs)
        finally:
            live.Painter.erase = keep


def build(meter):
    return score.adapt(NoErase, meter)
