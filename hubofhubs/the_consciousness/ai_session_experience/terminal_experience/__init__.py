"""Terminal rendering that needs no UI library: events in, blocks out.

``render(event, state)`` and ``settle(state)`` turn a run's progress events into ``Block`` values (see ``blocks.py``); a frontend
(a Textual app, a line REPL, plain text, JSON lines) only draws them. Core is the standard library plus this package. The wording
of the work summary and the asks is generic English (``strings.py``); a consumer app registers its own words with ``strings.register_overrides`` and owns any drift check.
Design and plan: ``docs/explanation/terminal-harness.md``.
"""
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.asks import Ask, AskAnswer, ask_block, ask_from_event, parse_answer
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.blocks import Block, clean, removed, to_text
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.render import (
    TerminalState, answer_ask, close_ask, fold_ask, live_line, render, settle, toggle_trail, toggle_updates, trail_blocks, unfold_ask)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.stopped import continue_message, stopped_block
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.updates import TurnMessage, earlier_preview, group, interim_message

__all__ = [
    "Ask", "AskAnswer", "Block", "TerminalState", "TurnMessage", "answer_ask", "ask_block", "ask_from_event", "clean", "close_ask",
    "continue_message", "earlier_preview", "fold_ask", "group", "interim_message", "live_line", "parse_answer", "removed", "render",
    "settle", "stopped_block", "to_text", "toggle_trail", "toggle_updates", "trail_blocks", "unfold_ask",
]
