"""Intake Sources (Body) and Request Intake (Consciousness): requests are taken in once, with their person."""
import json

from hubofhubs.consciousness.intake import EveryDeclaredSource
from hubofhubs.intake.queue import FolderQueue


def queue(tmp_path, rows):
    for index, row in enumerate(rows):
        (tmp_path / f"{index:03d}.json").write_text(json.dumps(row))
    return FolderQueue(str(tmp_path))


def test_the_folder_queue_hands_each_request_over_once_and_skips_what_is_not_a_request(tmp_path):
    source = queue(tmp_path, [{"text": "first", "person": "ana"}, {"text": "  "}, {"person": "bo"}, {"text": "second", "person": "bo", "source": "chat"}])
    (tmp_path / "bad.json").write_text("not json")
    assert source.sources()[0]["kind"] == "queued tasks"
    taken = source.pull()
    assert [(t["text"], t["person"], t["source"]) for t in taken] == [("first", "ana", "000"), ("second", "bo", "chat")]
    assert source.pull() == []


def test_request_intake_drops_duplicates_and_other_peoples_requests_and_keeps_order(tmp_path):
    source = queue(tmp_path, [{"text": "a", "person": "ana"}, {"text": "a", "person": "ana"}, {"text": "b", "person": "bo"}, {"text": "c"}])
    taken = EveryDeclaredSource(source).receive("ana")
    assert [t["text"] for t in taken] == ["a", "c"]
