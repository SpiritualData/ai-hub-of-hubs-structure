"""What a person is told while a turn runs: one communication policy over the Mind's transparency stream.

The Mind emits everything it does (plan, read, partial, status, interim, milestone, decision, result: the ``EVENT_*`` types in
``hubofhubs.the_world.tools.events``) and never decides what reaches the person. This module does, once, for every
surface. For each event, in the context of the turn so far, ``communicate`` returns one ``Delivery``:

* ``DELIVER_NOTHING``: the event stays in the transparency stream, inspectable on demand, and is never a message. This is the
  default for the raw Mind stream (plans, reads, model chunks, token counts, traces).
* ``DELIVER_STATUS``: shown to someone watching right now and REPLACED by the next thing they are shown; never kept in the
  conversation history. The first status of a turn is the acknowledgement (``hubofhubs.the_world.tools.acknowledge``),
  due before any slow work, within ``ack_within_seconds``. Later statuses mark a phase change. An interim the Mind marks
  ``data["announce"] is True`` (where things stand and what happens next, written before the work it announces) is a
  status too, however long the turn has run: it says what is coming, not what was found.
* ``DELIVER_DURABLE``: kept in the conversation, because the person would want to see it if they came back later. The final
  answer is durable. A partial result is durable when a long stretch of work produced something usable and another long
  stretch is still coming, so a person who left is not left with nothing; otherwise it is only a status.
* ``DELIVER_ASK``: durable AND a notification, for what the person must act on or know even when away: the run is blocked on
  them (a decision-request), or the Mind marked a finding as one to notify (``data["notify"] is True``).

Every decision reads structure only (the event's type, its data flags, elapsed and expected time, whether the event
carries usable content), never the words. The long stretch is a parameter with a default.

How a surface maps the deliveries (one consumer's mapping): ``DELIVER_STATUS`` is a status frame that the next frame replaces,
``DELIVER_DURABLE`` a stored message (an interim message, or the final reply for a result), ``DELIVER_ASK`` a stored ask plus a
notification, ``DELIVER_NOTHING`` no frame at all (or an on-demand view such as a work trail).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from hubofhubs.the_world.tools.acknowledge import ACK_WITHIN_SECONDS, STATUS_KIND_ACK
from hubofhubs.the_world.tools.events import (
    EVENT_DECISION, EVENT_INTENT, EVENT_INTERIM, EVENT_MILESTONE, EVENT_RESULT, EVENT_STATUS)

DELIVER_NOTHING = "nothing"
DELIVER_STATUS = "status"
DELIVER_DURABLE = "durable"
DELIVER_ASK = "ask"

#: Seconds of work that make a stretch long. A partial result after a stretch this long, with at least this much still to
#: come, is kept for a person who may have left.
LONG_STRETCH_SECONDS = 30.0

#: Why each delivery was chosen (stable strings for logs and tests).
REASON_ACK = "ack"
REASON_PHASE = "phase_change"
REASON_FINAL = "final_answer"
REASON_BLOCKED = "blocked_on_person"
REASON_NOTIFY = "marked_to_notify"
REASON_KEPT_FOR_LATER = "usable_after_long_stretch_more_coming"
REASON_NOTHING_USABLE = "nothing_usable"
REASON_SHORT_STRETCH = "short_stretch"
REASON_ENDING_SOON = "ending_soon"
REASON_MIND_STREAM = "mind_stream"
REASON_ANNOUNCE = "announces_work"

#: The ``data`` key with which the Mind marks an interim that announces the work to come rather than a result of it.
ANNOUNCE_KEY = "announce"


@dataclass(frozen=True)
class CommunicationPolicy:
    """The policy's parameters. The defaults are the hub's; a consumer may pass its own."""
    ack_within_seconds: float = ACK_WITHIN_SECONDS
    long_stretch_seconds: float = LONG_STRETCH_SECONDS


DEFAULT_COMMUNICATION_POLICY = CommunicationPolicy()


@dataclass(frozen=True)
class TurnSoFar:
    """What the surface knows about the turn when an event arrives. Times are seconds since the turn started."""
    elapsed_seconds: float = 0.0
    #: When the last durable message of this turn went out (None: none yet, so the stretch began at the turn's start).
    last_durable_at: Optional[float] = None
    #: How much work is still expected, when the Mind or the surface can say (None: unknown).
    expected_remaining_seconds: Optional[float] = None


@dataclass(frozen=True)
class Delivery:
    kind: str                 # DELIVER_NOTHING | DELIVER_STATUS | DELIVER_DURABLE | DELIVER_ASK
    reason: str
    notify: bool = False      # True only for DELIVER_ASK
    ack: bool = False         # True for the turn's acknowledgement status

    @property
    def shown(self) -> bool:
        return self.kind != DELIVER_NOTHING

    @property
    def kept(self) -> bool:
        """Stored in the conversation history (DELIVER_DURABLE or DELIVER_ASK)."""
        return self.kind in (DELIVER_DURABLE, DELIVER_ASK)


def event_parts(event: Any) -> tuple:
    """``(type, text, data)`` of a ``ProgressEvent``, its ``to_dict()``, or a wire dict (``event`` key for the type)."""
    if isinstance(event, Mapping):
        etype = event.get("type") or event.get("event")
        data = event.get("data") if isinstance(event.get("data"), Mapping) else {}
        if event.get("kind") and "kind" not in data:
            data = {**data, "kind": event.get("kind")}
        return etype, event.get("text") or "", data
    data = getattr(event, "data", None)
    return getattr(event, "type", None), getattr(event, "text", None) or "", data if isinstance(data, Mapping) else {}


def has_usable_content(text: str, data: Mapping[str, Any]) -> bool:
    """A partial result is usable when it carries content of its own: text, or a ``done`` part (what was found)."""
    return bool((text or "").strip() or str(data.get("done") or "").strip())


def communicate(event: Any, turn: TurnSoFar = TurnSoFar(), policy: CommunicationPolicy = DEFAULT_COMMUNICATION_POLICY) -> Delivery:
    """The one decision: how the person is told about ``event`` (see the module docstring)."""
    etype, text, data = event_parts(event)
    if etype == EVENT_STATUS:
        if data.get("kind") == STATUS_KIND_ACK:
            return Delivery(DELIVER_STATUS, REASON_ACK, ack=True)
        return Delivery(DELIVER_STATUS, REASON_PHASE)
    if etype == EVENT_INTENT:
        return Delivery(DELIVER_STATUS, REASON_PHASE)
    if etype == EVENT_DECISION:
        return Delivery(DELIVER_ASK, REASON_BLOCKED, notify=True)
    if etype == EVENT_RESULT:
        return Delivery(DELIVER_DURABLE, REASON_FINAL)
    if etype in (EVENT_INTERIM, EVENT_MILESTONE):
        if not has_usable_content(text, data):
            return Delivery(DELIVER_NOTHING, REASON_NOTHING_USABLE)
        if data.get(ANNOUNCE_KEY) is True:
            return Delivery(DELIVER_STATUS, REASON_ANNOUNCE)
        if data.get("notify") is True:
            return Delivery(DELIVER_ASK, REASON_NOTIFY, notify=True)
        stretch = turn.elapsed_seconds - (turn.last_durable_at or 0.0)
        if stretch < policy.long_stretch_seconds:
            return Delivery(DELIVER_STATUS, REASON_SHORT_STRETCH)
        remaining = turn.expected_remaining_seconds
        if data.get("final") is True or (remaining is not None and remaining < policy.long_stretch_seconds):
            return Delivery(DELIVER_STATUS, REASON_ENDING_SOON)
        return Delivery(DELIVER_DURABLE, REASON_KEPT_FOR_LATER)
    return Delivery(DELIVER_NOTHING, REASON_MIND_STREAM)


class TurnCommunicator:
    """``communicate`` with the turn's clock kept for the surface: build one when the turn starts, call ``decide`` for each
    event. A kept delivery restarts the stretch."""

    def __init__(self, policy: CommunicationPolicy = DEFAULT_COMMUNICATION_POLICY, *, clock: Callable[[], float] = time.monotonic):
        self.policy = policy
        self._clock = clock
        self.started_at = clock()
        self.last_durable_at: Optional[float] = None

    def elapsed(self) -> float:
        return self._clock() - self.started_at

    def decide(self, event: Any, *, expected_remaining_seconds: Optional[float] = None) -> Delivery:
        now = self.elapsed()
        delivery = communicate(event, TurnSoFar(elapsed_seconds=now, last_durable_at=self.last_durable_at,
                                                expected_remaining_seconds=expected_remaining_seconds), self.policy)
        if delivery.kept:
            self.last_durable_at = now
        return delivery
