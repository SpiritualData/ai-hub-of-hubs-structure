"""The V4A patch of OpenAI's apply_patch tool and the arm that reads OpenAI's tool calls: scripted operations in a temporary folder."""
import json

from hubofhubs.the_world.tools.agent_action_format.arms import ApplyPatchV4A
from hubofhubs.the_world.tools.agent_action_format.v4a import apply_operation


def test_create_update_delete_and_a_hunk_that_does_not_match(tmp_path):
    assert apply_operation(str(tmp_path), {"type": "create_file", "path": "d/a.py", "diff": "+def fib(n):\n+    return n\n"})[0]
    assert (tmp_path / "d/a.py").read_text() == "def fib(n):\n    return n\n"
    ok, text = apply_operation(str(tmp_path), {"type": "update_file", "path": "d/a.py", "diff": "@@\n-def fib(n):\n+def fibonacci(n):\n     return n"})
    assert ok and (tmp_path / "d/a.py").read_text() == "def fibonacci(n):\n    return n\n"
    ok, text = apply_operation(str(tmp_path), {"type": "update_file", "path": "d/a.py", "diff": "@@\n-nothing like this\n+x"})
    assert not ok and "does not match" in text and "fibonacci" in (tmp_path / "d/a.py").read_text()
    assert apply_operation(str(tmp_path), {"type": "delete_file", "path": "d/a.py"})[0] and not (tmp_path / "d/a.py").exists()


def test_a_path_outside_the_folder_is_refused(tmp_path):
    ok, text = apply_operation(str(tmp_path), {"type": "create_file", "path": "../x.txt", "diff": "+x"})
    assert not ok and "outside" in text


def test_the_arm_runs_apply_patch_and_shell_calls(tmp_path):
    reply = json.dumps([{"name": "apply_patch", "input": {"type": "create_file", "path": "n.txt", "diff": "+hello"}},
                        {"name": "shell", "input": {"command": ["bash", "-lc", "cat n.txt"]}}, {"name": "nothing", "input": {}}])
    got = ApplyPatchV4A().execute(reply, str(tmp_path))
    assert [g["ok"] for g in got] == [True, True, False] and "hello" in got[1]["text"]
