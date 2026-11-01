"""Terminal rendering that needs no UI library: events in, blocks out.

``render(event, state)`` and ``settle(state)`` turn a run's progress events into ``Block`` values (see ``blocks.py``); a frontend
(a Textual app, a line REPL, plain text, JSON lines) only draws them. Core is the standard library plus this package. The wording
of the work summary and the asks is the Quest app's English (``strings.py``), kept equal by ``tests/test_terminal_drift.py``.
Design and plan: ``docs/explanation/terminal-harness.md``.
"""
from .asks import Ask, AskAnswer, ask_block, ask_from_event, parse_answer
from .blocks import Block, clean, removed, to_text
from .render import TerminalState, answer_ask, close_ask, fold_ask, live_line, render, settle, toggle_trail, toggle_updates, trail_blocks, unfold_ask
from .stopped import continue_message, stopped_block
from .updates import TurnMessage, earlier_preview, group, interim_message

__all__ = [
    "Ask", "AskAnswer", "Block", "TerminalState", "TurnMessage", "answer_ask", "ask_block", "ask_from_event", "clean", "close_ask",
    "continue_message", "earlier_preview", "fold_ask", "group", "interim_message", "live_line", "parse_answer", "removed", "render",
    "settle", "stopped_block", "to_text", "toggle_trail", "toggle_updates", "trail_blocks", "unfold_ask",
]
