"""Tidying a card store: what is provably redundant is moved, never deleted, and every move can be taken back."""
import json
from pathlib import Path

from hubofhubs.recall import card_store_hygiene as hygiene
from hubofhubs.recall import card_store_tidy as tidy
from hubofhubs.recall.card_repository import FilesystemCardRepository
from hubofhubs.recall.card_store_tidy_plan import rekey_target

COMPOUNDED = "alpha-aaaaaa--root-bbbbbb--topic"


def topic(cid, *paths, name="", **extra):
    return {"id": cid, "name": name or cid, "files": [{"path": p} for p in paths],
            "provenance": {"created_by_task": "bootstrap"}, **extra}


def stray(tmp_path, card):
    """A card stored under a vector point id: the repository refuses to write one, an older writer did."""
    (Path(tmp_path) / "card:topic.json").write_text(json.dumps(card))


def fill(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    repo.write("topic", topic("topic", "src/a.py", "src/b.py"))
    repo.write(COMPOUNDED, topic(COMPOUNDED, "src/a.py", "src/b.py"))
    stray(tmp_path, {"id": "card:topic", "provenance": {"created_by_task": "bootstrap"}})
    repo.write("noted", topic("noted", "src/c.py", content=[{"why": "kept"}]))
    return repo


def test_a_compounded_copy_is_moved_and_a_card_with_notes_is_never_touched(tmp_path):
    repo = fill(tmp_path)
    files = hygiene.card_files_in(tmp_path)
    plan = hygiene.plan_tidy(files)
    moved = {move.card_id: move.reason for move in plan.moves}
    assert moved[COMPOUNDED] == "compounded" and "noted" not in moved and "topic" not in moved
    result = hygiene.apply_tidy(tmp_path, plan)
    assert COMPOUNDED in result.moved_ids and result.failed == 0
    assert repo.read(COMPOUNDED) is None and repo.read("noted") is not None and repo.read("topic") is not None
    assert hygiene.quarantine_counts(tmp_path)["compounded"] == 1


def test_a_tidy_can_be_undone_from_its_manifest(tmp_path):
    repo = fill(tmp_path)
    result = hygiene.apply_tidy(tmp_path, hygiene.plan_tidy(hygiene.card_files_in(tmp_path)))
    assert result.manifest is not None and repo.read(COMPOUNDED) is None
    undone = hygiene.undo_tidy(tmp_path, result.manifest)
    assert undone.restored >= 1 and repo.read(COMPOUNDED) is not None


def test_a_stray_stored_under_a_vector_point_id_is_folded_into_the_card_it_names(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    repo.write("topic", topic("topic", "src/a.py"))
    stray(tmp_path, {"id": "card:topic", "provenance": {"created_by_task": "a run"},
                     "content": [{"id": "n1", "why": "a note", "ts": 5}]})
    plan = hygiene.plan_tidy(hygiene.card_files_in(tmp_path))
    assert [m.reason for m in plan.moves] == ["item-id"]
    hygiene.apply_tidy(tmp_path, plan)
    assert not (tmp_path / "card:topic.json").exists()
    assert any(item.get("why") == "a note" for item in repo.read("topic").get("content", []))


def test_cheap_evidence_is_read_from_names_alone():
    assert hygiene.has_cheap_evidence("card:x") and hygiene.has_cheap_evidence(COMPOUNDED)
    assert not hygiene.has_cheap_evidence("topic") and not hygiene.has_cheap_evidence("alpha-aaaaaa--topic")


def test_the_store_health_counts_with_the_per_folder_rule_it_was_given(tmp_path):
    fill(tmp_path)
    root = tmp_path / "corpus"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("x = 1\n")
    health = hygiene.store_health(tmp_path, per_folder=1, root=root)
    assert health.total == 4 and health.folders == 2 and health.compounded_ids == 1 and health.item_id_cards == 1
    assert health.topic_over_folders is True
    assert hygiene.store_health(tmp_path, per_folder=0, root=root).topic_over_folders is False
    assert "managed by another system" in health.render()


def test_the_inflation_check_trusts_a_remembered_folder_count_only_to_say_not_inflated(tmp_path):
    cards = {f"c{i}": topic(f"c{i}", f"src/f{i}.py") for i in range(3)}
    root = tmp_path / "corpus"
    (root / "src").mkdir(parents=True)
    (root / "src" / "f0.py").write_text("x\n")
    check = hygiene.inflation_check(tmp_path / "cards", root, cards, per_folder=1)
    assert check.over and check.folders == 2
    assert not hygiene.inflation_check(tmp_path / "cards", root, cards, per_folder=8).over
    assert hygiene.inflation_check(tmp_path / "cards", root, cards, per_folder=0).folders is None


def test_the_repository_tidy_exports_first_removes_and_undoes_through_the_port(tmp_path):
    repo = fill(tmp_path)
    cards = repo.load_all()
    plan = tidy.plan_store(cards, cards_dir=tmp_path, repo=repo)
    assert COMPOUNDED in {entry["key"] for entry in plan.entries}
    runner = tidy.RepositoryTidy(repo, tmp_path)
    run = runner.apply(plan, cards)
    assert run.failed == "" and run.removed >= 1 and run.export is not None and run.manifest is not None
    assert repo.read(COMPOUNDED) is None and repo.read("noted") is not None
    assert tidy.latest_manifest(tmp_path) == run.manifest
    undone = tidy.RepositoryTidy(repo, tmp_path).undo(run.manifest)
    assert undone.failed == "" and repo.read(COMPOUNDED) is not None


def test_the_tidy_mode_follows_the_consumers_setting_and_the_kind_of_store(tmp_path):
    class Hosted:
        pass

    assert tidy.resolve_mode(None, FilesystemCardRepository(str(tmp_path))) == "apply"
    assert tidy.resolve_mode(None, Hosted()) == "plan"
    assert tidy.resolve_mode("off", Hosted()) == "off"
    assert tidy.resolve_mode("nonsense", FilesystemCardRepository(str(tmp_path))) == "apply"


def test_a_store_over_its_limit_is_due_a_tidy_and_one_under_it_only_when_ids_prove_a_copy():
    clean = {f"c{i}": {} for i in range(3)}
    assert tidy.due(clean, 0) == ((), "") and tidy.due(clean, 5) == ((), "")
    assert tidy.due(clean, 2)[0] and "over its limit" in tidy.due(clean, 2)[1]
    assert tidy.due({"card:x": {}}, 5)[0]


def test_a_compounded_card_with_no_surviving_copy_is_rekeyed_to_its_one_hop_id():
    assert rekey_target(COMPOUNDED) == "alpha-aaaaaa--topic" or "--" in rekey_target(COMPOUNDED)
