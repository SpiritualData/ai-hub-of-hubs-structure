"""The quick acknowledgement contract: one status marked ``kind: "ack"``, sent once per turn, before slow work."""
import time

from hubofhubs.api import (ACK_TEXT, ACK_WITHIN_SECONDS, EVENT_INTERIM, EVENT_STATUS, STAGE_MODEL, STAGE_PLACEHOLDER, Acknowledger,
                           Emitter, Mode, STATUS_KIND_ACK, ack_event, ack_stage, is_ack, model_ack_event)


def test_the_ack_is_a_status_not_an_interim():
    event = ack_event()
    assert event.type == EVENT_STATUS and event.type != EVENT_INTERIM
    assert event.text == ACK_TEXT
    assert event.data == {"kind": STATUS_KIND_ACK}


def test_is_ack_reads_events_and_wire_dicts():
    assert is_ack(ack_event())
    assert is_ack(ack_event().to_dict())
    assert is_ack({"event": "status", "text": "Looking into this...", "kind": "ack"})
    assert not is_ack({"event": "status", "text": "Reading..."})
    assert not is_ack({"type": "interim", "text": "x", "data": {"kind": "ack"}})
    assert not is_ack("status")


def test_acknowledger_sends_once_and_meets_the_contract_before_slow_work():
    sent = []
    ack = Acknowledger(sent.append)
    assert ack.ack() is True
    time.sleep(0.05)   # the slow work comes after the ack
    assert ack.ack() is False, "a second layer calling ack sends nothing"
    assert len(sent) == 1 and is_ack(sent[0])
    assert ack.within_contract and ack.acked_after < ACK_WITHIN_SECONDS


def test_acknowledger_reports_a_late_ack_and_survives_a_failing_sink():
    now = [0.0]
    late = Acknowledger(lambda e: (_ for _ in ()).throw(RuntimeError("sink down")), clock=lambda: now[0])
    now[0] = ACK_WITHIN_SECONDS + 0.5
    assert late.ack() is True
    assert late.sent and not late.within_contract


class Sink:
    def __init__(self):
        self.events = []

    def update(self, event, mode):
        self.events.append(event)


def test_emitter_ack_goes_out_once_with_its_status_callback():
    sink, said = Sink(), []
    emit = Emitter(sink, Mode.LIVE, said.append)
    assert emit.ack() is True and emit.ack() is False
    emit.status("Reading...")
    assert [is_ack(e) for e in sink.events] == [True, False]
    assert said == [ACK_TEXT, "Reading..."]


def test_the_model_ack_is_a_second_stage_that_is_still_an_ack_status():
    event = model_ack_event("  I'll check your streak and compare it with last week.  ")
    assert event.type == EVENT_STATUS and is_ack(event)
    assert event.text == "I'll check your streak and compare it with last week."
    assert event.data == {"kind": STATUS_KIND_ACK, "stage": STAGE_MODEL}
    assert ack_stage(event) == STAGE_MODEL
    assert ack_stage(ack_event()) == STAGE_PLACEHOLDER, "an ack with no stage is the code-written placeholder"
    assert ack_stage({"event": "status", "text": "x", "kind": "ack", "stage": "model"}) == STAGE_MODEL
    assert ack_stage({"event": "status", "text": "Reading..."}) is None


def test_a_model_ack_needs_a_line_the_model_wrote():
    import pytest
    with pytest.raises(ValueError):
        model_ack_event("   ")


def test_emitter_sends_the_placeholder_first_then_the_model_ack_which_does_not_use_up_the_ack_once():
    sink, said = Sink(), []
    emit = Emitter(sink, Mode.LIVE, said.append)
    assert emit.ack() is True
    emit.model_ack("I'll look at your marathon plan.")
    assert [ack_stage(e) for e in sink.events] == [STAGE_PLACEHOLDER, STAGE_MODEL]
    assert said == [ACK_TEXT, "I'll look at your marathon plan."]
    assert emit.ack() is False, "the placeholder still goes out once"
