"""The quick acknowledgement a turn opens with: a status the person sees first, within a stated latency.

A person who sends a message should hear back at once, long before the answer is ready. The hub's answer is a
STATUS event (``EVENT_STATUS``) marked ``data["kind"] == "ack"``:

* It is a status, not a message. A consumer shows it first and REPLACES it with whatever the turn sends next (a
  later status, a partial result, an ask, the answer). It is never stored in the conversation history. That is
  the difference from ``EVENT_INTERIM``, a partial result the reader keeps.
* It is written by code from nothing but the fact that a turn started, so it costs no model call and no read.
  A consumer may pass its own fixed or code-written wording.
* The contract: a turn emits it within ``ACK_WITHIN_SECONDS`` of starting, BEFORE any model call, context
  search or other slow work. Whoever first holds the turn (a web endpoint the moment its stream opens, an
  orchestrator at the top of its run) sends it; ``Acknowledger`` makes the send happen once per turn and
  records how long it took, so a consumer or a test can check the contract.

Nothing here knows a consumer.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from hubofhubs.the_world.tools.deep import ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_STATUS

#: The ``data["kind"]`` that marks a status event as the turn's acknowledgement.
STATUS_KIND_ACK = "ack"

#: The default wording: says the request was received and work has started, claims nothing about the answer.
ACK_TEXT = "Looking into this..."

#: The latency contract, in seconds from the moment the turn starts to the moment the acknowledgement is emitted.
#: A surface adds its own transport time on top (a web stream's connection and authentication).
ACK_WITHIN_SECONDS = 1.0


def ack_event(text: str = ACK_TEXT) -> ProgressEvent:
    """The acknowledgement as a ``ProgressEvent``: a status marked ``kind: "ack"``."""
    return ProgressEvent(type=EVENT_STATUS, text=text or ACK_TEXT, data={"kind": STATUS_KIND_ACK})


def is_ack(event: Any) -> bool:
    """True when ``event`` (a ``ProgressEvent`` or its ``to_dict()`` / wire dict) is the acknowledgement."""
    if isinstance(event, ProgressEvent):
        etype, data, kind = event.type, event.data, None
    elif isinstance(event, dict):
        etype, data, kind = event.get("type") or event.get("event"), event.get("data"), event.get("kind")
    else:
        return False
    if etype != EVENT_STATUS:
        return False
    if kind == STATUS_KIND_ACK:
        return True
    return isinstance(data, dict) and data.get("kind") == STATUS_KIND_ACK


class Acknowledger:
    """Sends a turn's acknowledgement once and records when it went out.

    Build it when the turn starts (``started_at`` is taken then), call ``ack()`` before any slow work. A second
    ``ack()`` sends nothing, so two layers that each hold the turn (an endpoint and the orchestrator under it) can
    both call it safely when they share one ``Acknowledger``.
    """

    def __init__(self, emit: Callable[[ProgressEvent], Any], *, clock: Callable[[], float] = time.monotonic,
                 within_seconds: float = ACK_WITHIN_SECONDS):
        self._emit = emit
        self._clock = clock
        self.within_seconds = within_seconds
        self.started_at = clock()
        self.acked_after: Optional[float] = None

    @property
    def sent(self) -> bool:
        return self.acked_after is not None

    @property
    def within_contract(self) -> bool:
        """True when the acknowledgement went out inside ``within_seconds`` of the turn's start."""
        return self.acked_after is not None and self.acked_after <= self.within_seconds

    def ack(self, text: str = ACK_TEXT) -> bool:
        """Emit the acknowledgement if it has not gone out yet. Returns True when this call sent it. An emit
        failure is swallowed: the turn never depends on its acknowledgement."""
        if self.sent:
            return False
        self.acked_after = self._clock() - self.started_at
        try:
            self._emit(ack_event(text))
        except Exception:  # noqa: BLE001  the acknowledgement must never break the turn
            pass
        return True
