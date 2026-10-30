"""Merging a narrow store into a wider one: ids kept, paths prefixed, collisions renamed deterministically, the limit and the
vector points answered to, and a second run changing nothing. Settings are arguments."""
from pathlib import Path

from hubofhubs.recall import card_store_merge as merge
from hubofhubs.recall.card_repository import FilesystemCardRepository
from hubofhubs.recall.card_store_identity import read_meta, write_meta

NARROW_ID, WIDE_ID = "st_aaaaaaaaaaaaaaaa", "st_bbbbbbbbbbbbbbbb"


def make_store(root: Path, store_id: str, cards) -> str:
    cards_dir = root / ".cards"
    repo = FilesystemCardRepository(str(cards_dir))
    for cid, card in cards.items():
        repo.write(cid, card)
    write_meta(str(cards_dir), {"version": 1, "store_id": store_id, "root": str(root), "vector_id_scheme": "legacy"})
    return str(cards_dir)


def card(cid, *paths, name=""):
    return {"id": cid, "name": name or cid, "files": [{"path": p} for p in paths], "provenance": {"created_by_task": "bootstrap"}}


def stores(tmp_path, narrow_cards, wide_cards=None):
    narrow = make_store(tmp_path / "wide" / "sub", NARROW_ID, narrow_cards)
    wide = make_store(tmp_path / "wide", WIDE_ID, wide_cards or {})
    return narrow, wide


class FakeVectors:
    def __init__(self):
        self.moves, self.deleted, self.scopes = [], [], []

    def relabel_points(self, moves, *, scope, delete_old, apply):
        self.moves.append((list(moves), apply))
        self.scopes.append(scope)
        return len(moves)

    def delete_items(self, ids, *, scope):
        self.deleted.extend(ids)
        self.scopes.append(scope)
        return len(ids)


def test_cards_keep_their_ids_and_their_paths_gain_the_narrow_roots_prefix(tmp_path):
    narrow, wide = stores(tmp_path, {"topic": card("topic", "a.py", "pkg/b.py")})
    plan = merge.apply_merge(narrow, wide, max_cards=0)
    assert not plan.problems
    moved = FilesystemCardRepository(wide).read("topic")
    assert [f["path"] for f in moved["files"]] == ["sub/a.py", "sub/pkg/b.py"]
    assert FilesystemCardRepository(narrow).read("topic") is not None      # the source is kept without a prune


def test_a_second_run_changes_nothing(tmp_path):
    narrow, wide = stores(tmp_path, {"topic": card("topic", "a.py")})
    merge.apply_merge(narrow, wide, max_cards=0)
    again = merge.plan_merge(narrow, wide, max_cards=0)
    assert [mv.status for mv in again.moves] == [merge.STATUS_ALREADY]


def test_a_colliding_id_is_renamed_after_the_source_store_and_never_overwrites(tmp_path):
    narrow, wide = stores(tmp_path, {"topic": card("topic", "a.py", name="narrow topic")},
                          {"topic": card("topic", "other.py", name="wide topic")})
    plan = merge.apply_merge(narrow, wide, max_cards=0)
    renamed = f"topic{merge.RENAME_SEP}{NARROW_ID[3:11]}"
    assert [mv.status for mv in plan.moves] == [merge.STATUS_RENAMED]
    repo = FilesystemCardRepository(wide)
    assert repo.read("topic")["name"] == "wide topic" and repo.read(renamed)["name"] == "narrow topic"


def test_the_wide_stores_limit_stops_a_merge_and_names_the_setting(tmp_path):
    narrow, wide = stores(tmp_path, {"one": card("one", "a.py"), "two": card("two", "b.py")}, {"w": card("w", "w.py")})
    plan = merge.plan_merge(narrow, wide, max_cards=2, limit_name="MY_LIMIT")
    assert plan.problems and "MY_LIMIT" in plan.problems[0] and "3 cards" in plan.problems[0].replace(",", "")
    assert FilesystemCardRepository(wide).read("one") is None
    assert not merge.plan_merge(narrow, wide, max_cards=0).problems


def test_pruning_the_source_records_where_its_cards_went(tmp_path):
    narrow, wide = stores(tmp_path, {"topic": card("topic", "a.py")})
    merge.apply_merge(narrow, wide, max_cards=0, prune_source_after=True)
    assert FilesystemCardRepository(narrow).read("topic") is None
    assert read_meta(narrow).get("merged_into")
    assert any(entry.get("store_id") == NARROW_ID for entry in read_meta(wide).get("merged_from", []))


def test_state_folders_are_copied_except_the_vector_folders_the_consumer_names(tmp_path):
    narrow, wide = stores(tmp_path, {"topic": card("topic", "a.py")})
    (Path(narrow) / "turns").mkdir()
    (Path(narrow) / "turns" / "t1.json").write_text("{}")
    (Path(narrow) / "vectors").mkdir()
    (Path(narrow) / "vectors" / "segment").write_text("x")
    merge.apply_merge(narrow, wide, max_cards=0, vector_dirs=("vectors",))
    assert (Path(wide) / "turns" / "t1.json").exists() and not (Path(wide) / "vectors").exists()


def test_vector_points_are_relabelled_in_the_scope_the_consumer_names_and_the_embedder_is_never_called(tmp_path):
    narrow, wide = stores(tmp_path, {"topic": card("topic", "a.py")})
    vectors = FakeVectors()
    scope = {"point_class": "card_seed"}
    plan = merge.apply_merge(narrow, wide, max_cards=0, seed_scope=scope, vector_store=vectors)
    assert plan.vectors_checked and vectors.moves
    moves, applied = vectors.moves[-1]
    assert applied is True and moves[0].paths == ("sub/a.py",) and moves[0].old_item_id == "card:topic"
    assert all(s == scope for s in vectors.scopes)
