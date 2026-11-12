"""A deliberately broken arm (revision 4): the reference terminal whose view of a helper is indented by four columns for each level it is down and stacks a breadcrumb for each level, so the
content narrows and the header grows the deeper in. The depth checks must catch it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import live  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession  # noqa: E402


def indented(original):
    def draw(view, width=80, color=False, rows=8, transcript=False):
        lines = original(view, width, color, rows, transcript)
        depth = view.focus.depth
        if not depth:
            return lines
        at = next((i for i, row in enumerate(lines) if row.startswith("main") and (" > " in row or " \u203a " in row)), None)
        if at is None:
            return lines
        stacked = [lines[at]] * depth                      # one header row for each level
        body = [" " * (4 * depth) + row for row in lines[at + 1:-2]]      # the content pushed right by each level
        return lines[:at] + stacked + body + lines[-2:]
    return draw


class IndentsPerDepth(LiveSession):
    def attend(self, harness, goal, out, keys=None, *args, **kwargs):
        original = live.frame
        live.frame = indented(original)
        try:
            return super().attend(harness, goal, out, keys, *args, **kwargs)
        finally:
            live.frame = original


def build(meter):
    return score.adapt(IndentsPerDepth, meter)
