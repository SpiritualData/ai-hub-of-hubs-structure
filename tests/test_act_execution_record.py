"""The per-turn execution record: what actually executed, told apart from what was only requested."""
from hubofhubs.act.execution_record import ExecutionFact, ExecutionRecord, classify_exec_phase


def test_an_empty_record_says_nothing_executed():
    record = ExecutionRecord()
    assert not record.any_mutation_attempted and not record.any_success and not record.any_failure
    assert "NO action/operation executed" in record.summary()
    assert record.to_dict() == {"facts": []}


def test_the_summary_names_success_failure_and_no_recorded_outcome():
    record = ExecutionRecord(facts=[ExecutionFact(goal="a", succeeded=True), ExecutionFact(goal="b", failed=True, error="boom"),
                                    ExecutionFact(goal="c")])
    text = record.summary()
    assert "'a': SUCCEEDED" in text and "'b': FAILED (boom)" in text and "'c': NO RECORDED OUTCOME" in text
    assert record.any_success and record.any_failure and record.any_mutation_attempted
    assert record.to_dict()["facts"][1] == {"goal": "b", "succeeded": False, "failed": True, "error": "boom"}


def test_exec_phases_classify_as_success_failure_or_in_flight():
    assert classify_exec_phase(" Done ") == "success" and classify_exec_phase("completed") == "success"
    assert classify_exec_phase("FAILED") == "failure" and classify_exec_phase("error") == "failure"
    assert classify_exec_phase("retrying") is None and classify_exec_phase(None) is None and classify_exec_phase(3) is None
