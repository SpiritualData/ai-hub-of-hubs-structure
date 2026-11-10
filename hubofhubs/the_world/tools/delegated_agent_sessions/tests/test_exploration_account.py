"""How much a run only looked before it first changed something, and the trail it leaves (``delegated_agent_sessions.session``).

Records are built here in the shape Claude Code writes them (a ``tool_use`` block, then a ``tool_result``); none is a real transcript. Offline."""
import json

from hubofhubs.the_world.tools.delegated_agent_sessions.session import (
    TrailStore, exploration_account, merge_trails, run_trail)


def use(i, name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}}


def result(i, error=False):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": i, "is_error": error}]}}


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def test_counts_looking_before_the_first_write(tmp_path):
    p = write(tmp_path / "s.jsonl", [
        use("1", "Read", file_path="/w/a.py"), use("2", "Grep", pattern="x"), use("3", "Glob", pattern="*.py"),
        use("4", "Bash", command="ls -la"), use("5", "Bash", command="cd /w && sed -n 1,5p b.py"),
        use("6", "Edit", file_path="/w/a.py"), result("6"), use("7", "Read", file_path="/w/c.py")])
    a = exploration_account(p)
    assert a["explore_before_first_write"] == 5
    assert a["explore_before_first_file_change"] == 5
    assert a["explore_total"] == 6
    assert a["tool_calls_total"] == 7
    assert a["first_write_index"] == 5
    assert a["files_read"] == ["/w/a.py", "b.py", "/w/c.py"]
    assert a["files_changed"] == ["/w/a.py"]


def test_a_shell_command_that_does_more_than_look_is_the_first_write(tmp_path):
    p = write(tmp_path / "s.jsonl", [use("1", "Bash", command="ls | grep x"), use("2", "Bash", command="cat a | python -c 1"),
                                     use("3", "Bash", command="grep x > out.txt"), use("4", "Read", file_path="/w/a")])
    a = exploration_account(p)
    assert a["first_write_index"] == 1
    assert a["explore_before_first_write"] == 1
    assert a["explore_before_first_file_change"] == 2   # no file edit came, so every look counts
    assert a["explore_total"] == 2


def test_a_run_that_never_wrote(tmp_path):
    p = write(tmp_path / "s.jsonl", [use("1", "Read", file_path="/w/a"), use("2", "Read", file_path="/w/a")])
    a = exploration_account(p)
    assert a["first_write_index"] is None
    assert a["explore_before_first_write"] == 2
    assert a["files_read"] == ["/w/a"]


def test_a_failed_edit_is_not_a_changed_file_and_cat_arguments_are_read(tmp_path):
    p = write(tmp_path / "s.jsonl", [use("1", "Bash", command="cat -n a.txt b.txt"), use("2", "Write", file_path="/w/x"), result("2", True)])
    a = exploration_account(p)
    assert a["files_read"] == ["a.txt", "b.txt"]
    assert a["files_changed"] == []
    assert a["first_write_index"] == 1


def test_subagent_records_count_and_files_read_are_capped(tmp_path):
    p = write(tmp_path / "s.jsonl", [use("1", "Agent", prompt="p")])
    write(tmp_path / "s" / "subagents" / "agent-1.jsonl",
          [use(f"r{n}", "Read", file_path=f"/w/f{n}") for n in range(50)] + [use("e", "Edit", file_path="/w/f0")])
    a = exploration_account(p)
    assert a["tool_calls_total"] == 52
    assert a["explore_total"] == 50
    assert a["explore_before_first_write"] == 50
    assert len(a["files_read"]) == 40


def test_unreadable_or_missing_record_gives_zeros(tmp_path):
    assert exploration_account(tmp_path / "none.jsonl")["tool_calls_total"] == 0
    assert exploration_account(None)["first_write_index"] is None
    (tmp_path / "bad.jsonl").write_text('{"x": "tool_use"\nnot json "tool_use"\n')
    assert exploration_account(tmp_path / "bad.jsonl")["tool_calls_total"] == 0


def test_run_trail_is_relative_and_drops_outside_paths(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    account = {"files_read": [str(work / "a.md"), str(work / "d" / "b.md"), "/etc/hosts", str(tmp_path / "other" / "c")],
               "files_changed": [str(work / "a.md"), "../elsewhere"]}
    assert run_trail(account, str(work)) == {"read": ["d/b.md"], "changed": ["a.md"]}
    assert run_trail(account, None) == {"read": [], "changed": []}


def test_merge_ranks_changed_first_then_by_runs_and_keeps_five():
    runs = [{"read": ["old.md"], "changed": []}] + [{"read": ["a.md", "b.md"], "changed": ["c.py"] if n == 4 else []} for n in range(5)]
    merged = merge_trails(runs)
    assert [m["path"] for m in merged] == ["c.py", "a.md", "b.md"]   # the oldest of six runs is no longer kept
    assert merged[0] == {"path": "c.py", "runs": 1, "changed": True}
    assert merged[1]["runs"] == 5


def test_store_keeps_last_five_runs_per_folder_and_key(tmp_path):
    store = TrailStore(str(tmp_path / "trails"))
    work = tmp_path / "work"
    work.mkdir()
    for n in range(7):
        assert store.record(str(work), "goal-1", {"read": [f"r{n}.md"], "changed": []})
    store.record(str(work), "goal-2", {"read": ["z.md"], "changed": ["y.py"]})
    assert [r["read"] for r in store.runs(str(work), "goal-1")] == [[f"r{n}.md"] for n in range(2, 7)]
    assert [f["path"] for f in store.ranked(str(work), "goal-2")] == ["y.py", "z.md"]
    assert store.ranked(str(work), "none") == [] and store.ranked(None, "goal-1") == []
    assert not store.record(str(work), "goal-1", {"read": [], "changed": []})
    assert len(TrailStore(str(tmp_path / "trails")).ranked(str(work), "goal-1", limit=2)) == 2   # survives a new instance


def test_store_failure_never_raises(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    store = TrailStore(str(blocker / "inside"))
    assert store.record(str(tmp_path), "g", {"read": ["a"], "changed": []}) is False
    assert store.ranked(str(tmp_path), "g") == []
