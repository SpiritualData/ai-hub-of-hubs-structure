"""The quick acknowledgement a turn opens with: a status the person sees first, in two stages inside a stated latency.

A person who sends a message should hear back at once, long before the answer is ready. The hub's answer is a
STATUS event (``EVENT_STATUS``) marked ``data["kind"] == "ack"``, sent in TWO stages:

1. The PLACEHOLDER (``stage`` absent or ``STAGE_PLACEHOLDER``). Written by code from nothing but the fact that a turn
   started, so it costs no model call and no read. It goes out within ``ACK_WITHIN_SECONDS`` of the turn starting,
   BEFORE any model call, context search or other slow work. A consumer may pass its own fixed or code-written wording.
2. The MODEL ACK (``stage == STAGE_MODEL``). One sentence, written by one fast-tier model call (a tier, never a model
   name), in the representative's voice, that answers what the person actually asked ("I'll check your streak and
   compare it with last week."). The call starts at the turn's start, concurrently with context assembly, and the
   reply path never waits for it. Target: on screen within 1 to 3 seconds of the turn starting. If it is not ready
   before the turn's next beat or the final reply, or the call fails, it is DROPPED, and the drop or failure is logged
   and counted, never silent. It claims nothing the turn has not found yet.

Both stages share one contract:

* It is a status, not a message. A consumer shows the placeholder first, REPLACES it with the model ack when that
  arrives, and replaces that with whatever the turn sends next (a later status, a partial result, an ask, the
  answer). It is never stored in the conversation history. That is the difference from ``EVENT_INTERIM``, a partial
  result the reader keeps.
* Whoever first holds the turn (a web endpoint the moment its stream opens, an orchestrator at the top of its run)
  sends the placeholder; ``Acknowledger`` makes that send happen once per turn and records how long it took, so a
  consumer or a test can check the contract. The model ack is sent by whatever runs the model call, through
  ``model_ack_event``; ``ack_stage`` tells a consumer which stage an event is.

Nothing here knows a consumer.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from hubofhubs.the_world.tools.deep import ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_STATUS

#: The ``data["kind"]`` that marks a status event as the turn's acknowledgement.
STATUS_KIND_ACK = "ack"

#: ``data["stage"]`` of the code-written placeholder (an ack with no stage is the placeholder too).
STAGE_PLACEHOLDER = "placeholder"

#: ``data["stage"]`` of the model-written acknowledgement that replaces the placeholder.
STAGE_MODEL = "model"

#: The latency target for the model ack, in seconds from the turn's start: shown within this window or dropped.
MODEL_ACK_TARGET_SECONDS = 3.0

#: The default wording: says the request was received and work has started, claims nothing about the answer.
ACK_TEXT = "Looking into this..."

#: The latency contract, in seconds from the moment the turn starts to the moment the acknowledgement is emitted.
#: A surface adds its own transport time on top (a web stream's connection and authentication).
ACK_WITHIN_SECONDS = 1.0


def ack_event(text: str = ACK_TEXT) -> ProgressEvent:
    """The acknowledgement as a ``ProgressEvent``: a status marked ``kind: "ack"``."""
    return ProgressEvent(type=EVENT_STATUS, text=text or ACK_TEXT, data={"kind": STATUS_KIND_ACK})


def model_ack_event(text: str) -> ProgressEvent:
    """The model-written acknowledgement as a ``ProgressEvent``: an ack status marked ``stage: "model"``. ``text`` is the line
    the model wrote; an empty line is not an acknowledgement, so there is no default wording."""
    if not (text or "").strip():
        raise ValueError("a model acknowledgement needs the line the model wrote")
    return ProgressEvent(type=EVENT_STATUS, text=text.strip(), data={"kind": STATUS_KIND_ACK, "stage": STAGE_MODEL})


def ack_stage(event: Any) -> Optional[str]:
    """``STAGE_PLACEHOLDER`` or ``STAGE_MODEL`` for an acknowledgement (a ``ProgressEvent``, its ``to_dict()`` or a wire dict), else None."""
    if not is_ack(event):
        return None
    if isinstance(event, ProgressEvent):
        stage = (event.data or {}).get("stage")
    else:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        stage = event.get("stage") or data.get("stage")
    return STAGE_MODEL if stage == STAGE_MODEL else STAGE_PLACEHOLDER


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
