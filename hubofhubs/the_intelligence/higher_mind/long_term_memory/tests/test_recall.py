"""Long-Term Memory arms: retain across instances, keep people apart, expire, and rank by relevance then recency."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_body.internal_context.card_store.cardstore import LocalCardStore  # noqa: E402
from hubofhubs.the_intelligence.higher_mind.long_term_memory.interface import LongTermMemory  # noqa: E402
from hubofhubs.the_intelligence.higher_mind.long_term_memory.recall import CardStoreRecall, FileRecall, RecentWindow  # noqa: E402

NOW = "2026-07-12T09:00:00Z"


def test_a_later_instance_recalls_what_an_earlier_one_retained(tmp_path):
    FileRecall(str(tmp_path)).retain({"id": "a", "text": "Chose tomato seedlings", "at": "2026-07-01T00:00:00Z"}, "ana")
    got = FileRecall(str(tmp_path)).recall("tomato seedlings", "ana", now=NOW)
    assert [i["id"] for i in got] == ["a"] and FileRecall(str(tmp_path)).recall("tomato", "ben", now=NOW) == []


def test_all_arms_satisfy_the_interface_and_expire_old_items(tmp_path):
    for arm in (FileRecall(str(tmp_path)), CardStoreRecall(LocalCardStore()), RecentWindow(str(tmp_path / "w"))):
        assert isinstance(arm, LongTermMemory)
        arm.retain({"id": "old", "text": "tomato note", "at": "2025-01-01T00:00:00Z"}, "ana")
        arm.retain({"id": "new", "text": "tomato note", "at": "2026-07-10T00:00:00Z"}, "ana")
        assert [i["id"] for i in arm.recall("tomato note", "ana", now=NOW)] == ["new"]


def test_the_newer_leads_on_a_tie_and_the_same_id_is_replaced():
    arm = CardStoreRecall(LocalCardStore())
    arm.retain({"id": "a", "text": "tomato note", "at": "2026-07-01T00:00:00Z"}, "ana")
    arm.retain({"id": "b", "text": "tomato note", "at": "2026-07-05T00:00:00Z"}, "ana")
    arm.retain({"id": "a", "text": "tomato note", "at": "2026-07-09T00:00:00Z"}, "ana")
    assert [i["id"] for i in arm.recall("tomato note", "ana", now=NOW)] == ["a", "b"]


def test_an_arm_without_a_folder_leaves_no_temporary_folder_behind():
    import gc
    arm = FileRecall()
    arm.retain({"id": "a", "text": "tomato note", "at": "2026-07-10T00:00:00Z"}, "ana")
    folder = arm.directory
    assert folder.is_dir()
    del arm
    gc.collect()
    assert not folder.exists()


def test_scoring_cases_leave_no_memory_folder_behind(tmp_path, monkeypatch):
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "evaluation" / "long_term_memory"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "evaluation"))
    from score import adapt
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    run = adapt(FileRecall, None)
    args = dict(items=[dict(id="a", text="tomato note", at="2026-07-10T00:00:00Z", person="ana")], query="tomato", person="ana", limit=3, now=NOW)
    assert run("recall", args) == ["a"]
    assert list(tmp_path.iterdir()) == []
