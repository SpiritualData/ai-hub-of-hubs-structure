"""The deep-work ports: the run result, the progress event, the writer and sink Protocols, and the runner bases."""
import pytest

from hubofhubs.ports import deep, events


class Runner(deep.DeepRunnerBase):
    def run_goal(self, *, goal, brief, model=None, max_turns=None, emit=None, context_preamble=None, run_id=None):
        return deep.DeepResult(met=True, output=goal)


def test_a_runner_base_defaults_to_a_full_agent_that_uses_the_deep_model():
    runner = Runner()
    assert runner.write_surface == deep.WRITE_SURFACE_AGENT and deep.runner_uses_deep_model(runner)
    assert not deep.runner_starts_background_work(runner) and not deep.runner_uses_deep_model(None)
    assert runner.future_context_channel == deep.FUTURE_CONTEXT_VIA_OUTPUT
    assert isinstance(runner, deep.DeepRunner)


def test_a_duck_typed_runner_keeps_the_defaults():
    class Duck:
        pass
    assert deep.runner_uses_deep_model(Duck()) and not deep.runner_starts_background_work(Duck())


def test_the_runner_base_is_abstract():
    with pytest.raises(TypeError):
        deep.DeepRunnerBase()


def test_a_progress_event_serialises_only_what_it_holds():
    assert deep.ProgressEvent(type=events.EVENT_STATUS).to_dict() == {"type": "status"}
    event = deep.ProgressEvent(type=events.EVENT_RESULT, text="done", data={"k": 1})
    assert event.to_dict() == {"type": "result", "text": "done", "data": {"k": 1}}


def test_a_write_result_is_a_value_and_a_writer_base_needs_both_methods():
    refused = deep.WriteResult(ok=False, rel_path="a.txt", error="outside the root")
    assert not refused.ok and refused.bytes_written == 0 and refused.backup_path is None

    class Half(deep.FileWriterBase):
        def read_file(self, rel_path):
            return None
    with pytest.raises(TypeError):
        Half()

    class Ops(deep.OperationWriterBase):
        def write_operation(self, name, args):
            return deep.WriteResult(ok=True, rel_path=name)
    assert Ops().list_writable_operations() == [] and Ops().write_operation("x", {}).ok


def test_the_modes_and_the_surfacing_events():
    assert {m.value for m in events.Mode} == {"live", "background"}
    assert events.EVENT_RESULT in events.SURFACING_EVENTS and events.EVENT_EXEC not in events.SURFACING_EVENTS


def test_a_run_control_defaults_to_no_messages_no_cancel_no_pause():
    from hubofhubs.ports.control import ControlMessage, RunControl
    control = RunControl()
    assert control.claim_inputs() == [] and not control.cancel_requested() and not control.pause_requested()
    control.mark_seen(["m1"], "deep_worker")
    assert ControlMessage(id="m1", text="hello").text == "hello" and control.poll_seconds == 2.0


def test_a_deep_result_declares_no_coverage_by_default_and_carries_one_as_plain_data():
    assert deep.DeepResult(met=True).coverage is None
    declared = {"processed": 200, "total": 344, "unit": "entries", "complete": False, "capped": True}
    assert deep.DeepResult(met=False, coverage=declared).coverage == declared


def test_the_interim_event_type_is_its_own_string_and_does_not_surface_in_the_background():
    assert events.EVENT_INTERIM == "interim" and events.EVENT_INTERIM not in events.SURFACING_EVENTS
    event = deep.ProgressEvent(type=events.EVENT_INTERIM, text="so far", data={"final": False, "coverage": None})
    assert event.to_dict() == {"type": "interim", "text": "so far", "data": {"final": False, "coverage": None}}
