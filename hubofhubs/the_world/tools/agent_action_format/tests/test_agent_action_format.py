"""Agent Action Format: each arm reads its formats and only its formats; the reader of either takes both. Scripted replies, no model call."""
import json

from hubofhubs.the_world.tools.agent_action_format.arms import AnyFormat, NativeToolCalls, TextProtocol

NATIVE = json.dumps([{"name": "Write", "input": {"file_path": "d/a.txt", "content": "A"}}, {"name": "Bash", "input": {"command": "cat d/a.txt > b.txt"}}])
MARKUP = '<invoke name="RUN">\nRUN: echo wrapped > w.txt\n</parameter>\n</invoke>\nREPORT: ok'


def test_native_tool_calls_run_in_order_and_a_second_read_sees_the_first_write(tmp_path):
    got = NativeToolCalls().execute(NATIVE, str(tmp_path))
    assert [o["kind"] for o in got] == ["edit", "run"] and all(o["ok"] for o in got) and (tmp_path / "b.txt").read_text() == "A"


def test_a_native_edit_that_is_not_unique_and_a_path_outside_are_refused(tmp_path):
    (tmp_path / "a.py").write_text("x\nx\n")
    got = NativeToolCalls().execute(json.dumps([{"name": "Edit", "input": {"file_path": "a.py", "old_string": "x", "new_string": "y"}},
                                                {"name": "Write", "input": {"file_path": "../out.txt", "content": "no"}}]), str(tmp_path))
    assert [o["ok"] for o in got] == [False, False] and (tmp_path / "a.py").read_text() == "x\nx\n" and not (tmp_path.parent / "out.txt").exists()


def test_each_reader_takes_only_its_own_format_and_the_either_reader_takes_both(tmp_path):
    assert TextProtocol().execute(NATIVE, str(tmp_path)) == [] and NativeToolCalls().execute(MARKUP, str(tmp_path)) == []
    assert len(AnyFormat().execute(NATIVE, str(tmp_path))) == 2
    assert len(AnyFormat().execute(MARKUP, str(tmp_path))) == 1 and (tmp_path / "w.txt").read_text().strip() == "wrapped"
