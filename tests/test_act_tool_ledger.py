"""The tool-call ledger: what each call answered, kept by the runner; repeated unrecovered failures are told from fresh ones."""
from hubofhubs.act.tool_ledger import (FileToolLedger, alike, changed_something, describe_failure, failure_signature,
                                       outcome_from_result, repeated_failure, unrecovered_failures)


def test_a_failure_signature_blanks_ids_and_numbers_but_keeps_the_status():
    first = failure_signature("read", "HTTP 500: goal_deadbeef0123 failed after 12 ms")
    second = failure_signature("read", "HTTP 500: goal_cafebabe0456 failed after 90 ms")
    assert first == second and "|500|" in first
    assert failure_signature("read", "HTTP 403: nope") != failure_signature("read", "HTTP 500: nope")


def test_the_ledger_keeps_a_window_per_task(tmp_path):
    ledger = FileToolLedger(str(tmp_path))
    ledger.record("t1", outcome_from_result("read", False, "HTTP 500: boom", False))
    mark = ledger.mark("t1")
    ledger.record("t1", outcome_from_result("write", True, "done", True))
    ledger.record(None, outcome_from_result("write", True, "ignored", True))
    window = ledger.since("t1", mark)
    assert [c.tool for c in window] == ["write"] and changed_something(window)
    assert ledger.since("other", 0) == [] and ledger.mark(None) == 0


def test_a_failure_repeated_across_two_windows_is_a_broken_tool():
    failing = outcome_from_result("read", False, "HTTP 500: boom", False)
    previous, current = unrecovered_failures([failing]), unrecovered_failures([failing])
    assert repeated_failure(previous, current).tool == "read"
    recovered = unrecovered_failures([failing, outcome_from_result("read", True, "ok", False)])
    assert recovered == {} and repeated_failure(previous, recovered) is None
    assert "failed the same way on two attempts" in describe_failure(failing)


def test_alike_compares_two_texts_by_overlap_and_never_counts_two_empties():
    assert alike("The same words here", "the same words here", 0.8)
    assert not alike("", "", 0.8) and not alike("one thing", "something else entirely", 0.8)


def test_the_directory_name_is_the_callers():
    assert FileToolLedger(name="my-ledger").directory.endswith("my-ledger")
