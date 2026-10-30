"""The filesystem card repository: one JSON file per card, atomic writes, sidecars and quarantine excluded, never raises."""
import json

from hubofhubs.recall.card_repository import QUARANTINE_DIR_NAME, CardRepository, FilesystemCardRepository, card_embed_text


def test_the_repository_satisfies_the_port(tmp_path):
    assert isinstance(FilesystemCardRepository(str(tmp_path)), CardRepository)


def test_write_read_exists_delete_round_trip(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path / "cards"))
    assert repo.load_all() == {} and repo.read("a") is None and not repo.exists("a")
    assert repo.write("a", {"id": "a", "name": "Alpha"}) is True
    assert repo.read("a")["name"] == "Alpha" and repo.exists("a") and repo.count() == 1
    assert repo.delete("a") is True and repo.read("a") is None
    assert repo.delete("a") is True or repo.delete("a") is False  # never raises


def test_sidecars_temp_files_and_the_quarantine_are_not_cards(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    repo.write("real", {"id": "real"})
    (tmp_path / "bootstrap_meta.json").write_text("{}")
    (tmp_path / "folder_review.json").write_text("{}")
    (tmp_path / ".tmp_x.json").write_text("{}")
    (tmp_path / "broken.json").write_text("{not json")
    assert set(repo.load_all()) == {"real"}


def test_an_id_that_may_never_be_stored_is_refused_without_raising(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    assert repo.write("card:looks-like-a-vector-point", {"id": "x"}) is False
    assert repo.load_all() == {}


def test_a_quarantined_card_leaves_the_index_and_can_be_found_again(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    repo.write("a", {"id": "a"})
    assert repo.quarantine("a", "limit") is True
    assert not repo.exists("a") and repo.load_all() == {}
    held = repo.quarantined("a")
    assert held is not None and QUARANTINE_DIR_NAME in held.parts and json.loads(held.read_text())["id"] == "a"


def test_the_revision_changes_when_a_card_is_written(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    before = repo.revision()
    repo.write("a", {"id": "a"})
    assert repo.revision() != before


def test_the_embed_text_folds_name_description_notes_and_keywords():
    card = {"name": "Topic", "description": "About things", "keywords": ["k1", " "],
            "content": [{"why": "because"}, {"type": "note", "locator": {"text": "a note"}}]}
    text = card_embed_text(card)
    assert text.startswith("Topic\nAbout things") and "because" in text and "a note" in text and text.endswith("k1")
    assert card_embed_text({"summary": "only a summary"}) == "only a summary"
    assert card_embed_text(None) == ""
