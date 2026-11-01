"""A reply that stopped early: the plain reason and one way to continue."""
from __future__ import annotations

from typing import Optional

from .blocks import Block
from .strings import say

STOP_REASONS = ("budget", "stalled", "attempt_cap", "tool_fault")
#: What "Continue" sends as the next message (the Quest app sends the same word).
CONTINUE_MESSAGE_KEY = "questAIScreen.continueAnalysis.message"


def stopped_reason(outcome: str, stop_reason: str) -> Optional[str]:
    """The stop reason when the run itself marked the turn stopped WITH a known reason; otherwise None (nothing to add)."""
    return stop_reason if outcome == "stopped" and stop_reason in STOP_REASONS else None


def stopped_block(outcome: str, stop_reason: str, overrides=None, can_continue: bool = True) -> Optional[Block]:
    reason = stopped_reason(outcome, stop_reason)
    if reason is None:
        return None
    actions = (("continue", say("replyUpdates.stopped.continue", overrides)),) if can_continue else ()
    return Block(kind="stopped", text=say(f"replyUpdates.stopped.{reason}", overrides), state="stopped", fold_key="stopped",
                 style="muted", actions=actions)


def continue_message(overrides=None) -> str:
    return say(CONTINUE_MESSAGE_KEY, overrides)
