"""Command Execution: the arms over scripted cases (no model call), and the scratch folder that lasts the session."""
import shutil

import pytest

from hubofhubs.the_world.tools.command_execution.arms import BubblewrapWrapper, RefusalFloor

needs_bwrap = pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not installed")


def test_the_floor_runs_clips_times_out_and_refuses(tmp_path):
    arm = RefusalFloor()
    assert arm.run("echo hello", str(tmp_path)).output.strip() == "hello"
    assert arm.run("sudo ls", str(tmp_path)).refused
    assert arm.run("python3 -c \"print('x' * 20000)\"", str(tmp_path), limit=500).output.count("left out") == 1
    assert arm.run("sleep 20", str(tmp_path), timeout=0.5).timed_out


@needs_bwrap
def test_the_wrapper_contains_a_program_that_opens_a_path_itself_and_the_floor_does_not(tmp_path):
    work, outside = tmp_path / "work", tmp_path / "outside"
    work.mkdir()
    outside.mkdir()
    program = f"python3 -c \"open('{outside}/f.txt', 'w').write('x')\""
    RefusalFloor().run(program, str(work))
    assert (outside / "f.txt").exists()                     # the floor reads words: a program passes it
    (outside / "f.txt").unlink()
    done = BubblewrapWrapper().run(program, str(work))
    assert not (outside / "f.txt").exists() and done.code != 0


@needs_bwrap
def test_the_scratch_folder_lasts_across_commands_and_the_folder_is_writable(tmp_path):
    work, scratch = tmp_path / "work", tmp_path / "scratch"
    work.mkdir()
    scratch.mkdir()
    arm = BubblewrapWrapper()
    arm.run("echo kept > /tmp/n.txt && echo ok > here.txt", str(work), scratch=str(scratch))
    assert arm.run("cat /tmp/n.txt", str(work), scratch=str(scratch)).output.strip() == "kept" and (work / "here.txt").exists()
    assert arm.confined(str(work))


def test_without_bubblewrap_the_wrapper_says_it_is_not_confined(tmp_path):
    assert BubblewrapWrapper(program="no-such-program-here").confined(str(tmp_path)) is False
    assert BubblewrapWrapper(program="no-such-program-here").run("echo fine", str(tmp_path)).output.strip() == "fine"
