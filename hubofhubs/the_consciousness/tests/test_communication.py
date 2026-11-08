"""The communication policy: each Mind event becomes nothing, a status, a durable message or an ask, from structure only."""
from hubofhubs.api import (ANNOUNCE_KEY, DELIVER_ASK, DELIVER_DURABLE, DELIVER_NOTHING, DELIVER_STATUS, EVENT_DECISION, EVENT_INTERIM,
                           EVENT_MILESTONE, EVENT_PARTIAL, EVENT_PLAN, EVENT_READ, EVENT_RESULT, EVENT_STATUS,
                           EVENT_TOKENS, EVENT_WORK_TRACE, CommunicationPolicy, ProgressEvent, TurnCommunicator,
                           TurnSoFar, ack_event, communicate)


def interim(text="Found 12 of 40 rows so far.", **data):
    return ProgressEvent(type=EVENT_INTERIM, text=text, data={"final": False, **data})


def test_the_ack_is_the_first_status():
    d = communicate(ack_event())
    assert d.kind == DELIVER_STATUS and d.ack and not d.kept


def test_a_phase_change_is_a_status_that_is_not_kept():
    d = communicate(ProgressEvent(type=EVENT_STATUS, text="Reading your goals"))
    assert d.kind == DELIVER_STATUS and not d.ack and not d.kept


def test_the_raw_mind_stream_is_never_a_message():
    for etype in (EVENT_PLAN, EVENT_READ, EVENT_PARTIAL, EVENT_TOKENS, EVENT_WORK_TRACE):
        assert communicate(ProgressEvent(type=etype, text="internal")).kind == DELIVER_NOTHING


def test_the_final_answer_is_durable_and_a_block_on_the_person_is_an_ask():
    assert communicate(ProgressEvent(type=EVENT_RESULT, text="Done.")).kind == DELIVER_DURABLE
    ask = communicate(ProgressEvent(type=EVENT_DECISION, text="Which account?"))
    assert ask.kind == DELIVER_ASK and ask.notify and ask.kept


def test_a_partial_result_after_a_long_stretch_with_more_to_come_is_kept():
    turn = TurnSoFar(elapsed_seconds=45.0)
    assert communicate(interim(), turn).kind == DELIVER_DURABLE
    assert communicate(ProgressEvent(type=EVENT_MILESTONE, text="Draft written."), turn).kind == DELIVER_DURABLE


def test_a_partial_result_after_a_short_stretch_is_only_a_status():
    assert communicate(interim(), TurnSoFar(elapsed_seconds=10.0)).kind == DELIVER_STATUS
    # The stretch restarts at the last kept message.
    assert communicate(interim(), TurnSoFar(elapsed_seconds=50.0, last_durable_at=40.0)).kind == DELIVER_STATUS


def test_a_partial_result_just_before_the_end_is_only_a_status():
    assert communicate(interim(), TurnSoFar(elapsed_seconds=45.0, expected_remaining_seconds=5.0)).kind == DELIVER_STATUS
    assert communicate(interim(final=True), TurnSoFar(elapsed_seconds=45.0)).kind == DELIVER_STATUS


def test_a_partial_result_with_nothing_usable_is_nothing_and_a_marked_finding_notifies():
    assert communicate(interim(text=""), TurnSoFar(elapsed_seconds=90.0)).kind == DELIVER_NOTHING
    marked = communicate(interim(notify=True), TurnSoFar(elapsed_seconds=2.0))
    assert marked.kind == DELIVER_ASK and marked.notify


def test_wire_dicts_are_read_like_events():
    assert communicate({"event": "status", "text": "Looking into this...", "kind": "ack"}).ack
    assert communicate({"event": "interim", "text": "x", "data": {"final": False}},
                       TurnSoFar(elapsed_seconds=31.0)).kind == DELIVER_DURABLE


def test_the_long_stretch_is_a_parameter_and_the_communicator_keeps_the_clock():
    now = [0.0]
    talk = TurnCommunicator(CommunicationPolicy(long_stretch_seconds=10.0), clock=lambda: now[0])
    now[0] = 12.0
    assert talk.decide(interim()).kind == DELIVER_DURABLE
    now[0] = 15.0
    assert talk.decide(interim()).kind == DELIVER_STATUS, "the stretch restarted at the kept message"
    now[0] = 23.0
    assert talk.decide(interim()).kind == DELIVER_DURABLE


def test_an_interim_that_announces_the_work_is_a_status_however_long_the_turn_ran():
    turn = TurnSoFar(elapsed_seconds=90.0)
    d = communicate(interim(text="The goal stands at 3 of 10. Adding the two goals now.", **{ANNOUNCE_KEY: True}), turn)
    assert d.kind == DELIVER_STATUS and not d.kept
    assert communicate(interim(), turn).kind == DELIVER_DURABLE, "an unmarked partial result is still kept"
