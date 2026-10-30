"""Mounting card stores read-only, in place: discovery, readability, the path rebase and the guard against writing into a mount."""
from pathlib import Path

from hubofhubs.recall import card_store_mounts as mounts
from hubofhubs.recall.card_repository import FilesystemCardRepository
from hubofhubs.recall.card_store_identity import write_meta

FOLDER = ".cards"


def make_store(root: Path, store_id: str = "st_aaaaaaaaaaaaaaaa", cards=None, with_id: bool = True) -> Path:
    cards_dir = root / FOLDER
    repo = FilesystemCardRepository(str(cards_dir))
    for cid, card in (cards or {}).items():
        repo.write(cid, card)
    meta = {"version": 1, "root": str(root)}
    if with_id:
        meta["store_id"] = store_id
    write_meta(str(cards_dir), meta)
    return cards_dir


def card(cid, *paths):
    return {"id": cid, "name": cid, "files": [{"path": p} for p in paths], "provenance": {"created_by_task": "bootstrap"}}


def test_the_mount_mode_defaults_to_copy_and_opts_in_by_word():
    assert mounts.parse_mount_mode(None) == mounts.MODE_COPY and mounts.parse_mount_mode("") == mounts.MODE_COPY
    assert mounts.parse_mount_mode("off") == mounts.MODE_COPY
    assert all(mounts.parse_mount_mode(word) == mounts.MODE_MOUNT for word in ("1", "true", "Yes", "on", " mount "))


def test_a_directory_claims_its_subtree_only_with_a_bootstrapped_store_of_the_name_the_consumer_gave(tmp_path):
    make_store(tmp_path / "owner")
    assert mounts.claims_subtree(tmp_path / "owner", FOLDER) is True
    assert mounts.claims_subtree(tmp_path / "owner", ".elsewhere") is False
    (tmp_path / "plain").mkdir()
    assert mounts.claims_subtree(tmp_path / "plain", FOLDER) is False


def test_a_merged_store_no_longer_claims_its_subtree(tmp_path):
    cards_dir = make_store(tmp_path / "gone")
    write_meta(str(cards_dir), {"store_id": "st_aaaaaaaaaaaaaaaa", "merged_into": {"store_id": "st_bbbbbbbbbbbbbbbb"}})
    assert mounts.claims_subtree(tmp_path / "gone", FOLDER) is False


def test_nested_and_ancestor_stores_are_found_flat_and_the_readers_own_is_left_out(tmp_path):
    top = tmp_path / "top"
    own = make_store(top / "reader")
    make_store(top / "reader" / "inner")
    make_store(top)
    nested = mounts.discover_nested_stores(top / "reader", own, set(), store_dir_name=FOLDER)
    assert nested == [(top / "reader" / "inner").resolve()]
    above = mounts.discover_ancestor_stores(top / "reader", store_dir_name=FOLDER)
    assert above == [top.resolve()]


def test_resolve_mounts_mounts_what_is_readable_and_refuses_a_store_without_an_identity(tmp_path):
    reader_root = tmp_path / "reader"
    own = make_store(reader_root, "st_cccccccccccccccc")
    make_store(reader_root / "one", "st_aaaaaaaaaaaaaaaa")
    make_store(reader_root / "two", with_id=False)
    out = mounts.resolve_mounts(str(own), reader_root, set(), store_dir_name=FOLDER)
    assert [m.store_id for m in out.mounts] == ["st_aaaaaaaaaaaaaaaa"]
    assert len(out.refused) == 1 and "store_id" in out.refused[0][1]
    assert {Path(root).name for root in out.claimed_roots} == {"one", "two"}


def test_paths_are_rebased_against_the_two_real_roots():
    assert mounts.rebase_path("a.py", mounts.mount_prefix("/corpus/sub", "/corpus")) == "sub/a.py"
    assert mounts.rebase_path("lane/a.py", mounts.mount_prefix("/corpus", "/corpus/lane")) == "a.py"
    assert mounts.rebase_path("../outside.py", mounts.mount_prefix("/corpus/sub", "/corpus/sub")) is None
    assert mounts.rebase_path("", mounts.mount_prefix("/x", "/x")) is None
    assert mounts.rebase_path("/abs.py", mounts.mount_prefix("/x", "/y")) == "/abs.py"
    assert mounts.mounted_card_id("st_x", "topic") == "st_x:topic"


def test_a_reader_sees_a_mounted_card_rebased_and_can_never_write_into_it(tmp_path):
    owner_root = tmp_path / "reader" / "owner"
    owner_cards = make_store(owner_root, "st_aaaaaaaaaaaaaaaa", {"topic": card("topic", "src/a.py")})
    own = FilesystemCardRepository(str(make_store(tmp_path / "reader", "st_cccccccccccccccc")))
    mount = mounts.Mount(store_id="st_aaaaaaaaaaaaaaaa", cards_dir=str(owner_cards), root=str(owner_root))
    view = mounts.MountedCardRepository(own, str(tmp_path / "reader" / FOLDER), lambda: str(tmp_path / "reader"), lambda: [mount])
    cards = view.load_all()
    mounted = cards["st_aaaaaaaaaaaaaaaa:topic"]
    assert [f["path"] for f in mounted["files"]] == ["owner/src/a.py"]
    assert view.write("st_aaaaaaaaaaaaaaaa:topic", dict(mounted)) is False
    assert view.delete("st_aaaaaaaaaaaaaaaa:topic") is False
    assert FilesystemCardRepository(str(owner_cards)).read("topic") is not None
    assert view.write("own-card", card("own-card", "x.py")) is True and own.read("own-card") is not None


def test_the_copy_origin_of_an_imported_card_is_resolved_against_the_readers_root():
    imported = {"id": "c", "provenance": {"imported_from": "sub/lib"}}
    assert mounts.copy_origin_root(imported, "/corpus") == "/corpus/sub/lib"
    assert mounts.copy_origin_root({"id": "c"}, "/corpus") is None
