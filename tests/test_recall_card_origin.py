"""Where a card came from, and the rules that keep one card from becoming many: pure functions, rules passed in."""
from pathlib import Path

from hubofhubs.recall import card_origin as origin
from hubofhubs.recall.card_store_identity import write_meta


def bootstrap_card(**extra):
    return {"id": "c", "provenance": {"created_by_task": "bootstrap"}, **extra}


def test_an_id_never_repeats_a_namespace_segment_nor_looks_like_a_vector_item():
    assert origin.card_id_problem("a-111111--topic") == ""
    assert "twice" in origin.card_id_problem("a-111111--a-111111--topic")
    assert "vector" in origin.card_id_problem("card:topic")
    assert origin.card_id_problem("  ") == "the id is empty"
    assert origin.refuse("card:topic") and not origin.refuse("topic")


def test_item_ids_lose_only_their_own_store_qualifier():
    assert origin.card_id_of_item("card:st_aaaaaaaaaaaaaaaa:x", "st_aaaaaaaaaaaaaaaa") == "x"
    assert origin.card_id_of_item("card:st_bbbbbbbbbbbbbbbb:x", "st_aaaaaaaaaaaaaaaa") == "st_bbbbbbbbbbbbbbbb:x"
    assert origin.is_store_qualified("st_bbbbbbbbbbbbbbbb:x") and not origin.is_store_qualified("x")


def test_compounded_import_ids_are_recognised_from_the_id_alone():
    assert origin.compounding_evidence("topic") == ""
    assert origin.compounding_evidence("sub-abcdef--topic") == ""
    assert "root-" in origin.compounding_evidence("sub-abcdef--root-abcdef--topic")
    assert "2 import namespace" in origin.compounding_evidence("a-abcdef--b-123456--topic")


def test_an_import_id_is_a_function_of_the_origin_only():
    assert origin.import_id("sub/dir", "topic") == origin.import_id("sub/dir", "topic")
    assert origin.import_id("sub/dir", "topic") != origin.import_id("other", "topic")
    assert len(origin.import_id("x/" * 300, "topic")) <= origin.MAX_ID_CHARS


def test_protection_names_what_no_file_can_regenerate():
    assert origin.protection(bootstrap_card()) == ""
    assert origin.protection(bootstrap_card(managed_by="x")) == "managed by another system"
    assert origin.protection(bootstrap_card(usage_count=2)) == "has been used"
    assert origin.protection({"id": "c"}) == "written by a person (no provenance)"
    assert origin.protection(bootstrap_card(content=[])) == "has notes or edits added by a run"
    assert origin.protection(bootstrap_card(scope_tags=["team:1"])) == "carries scope tags"
    assert origin.protection(bootstrap_card(conventions=["c"])) == "carries conventions"


def test_an_edit_after_the_index_wrote_the_card_protects_it():
    card = bootstrap_card(summary="s")
    origin.stamp_index_hash(card)
    assert origin.matches_index_hash(card) and origin.protection(card) == ""
    card["summary"] = "edited by hand"
    assert origin.protection(card) == "edited by hand since the index wrote it"
    assert origin.protection(card, check_edits=False) == ""


def test_an_exported_origin_is_found_under_the_store_folder_the_consumer_names(tmp_path):
    far = tmp_path / "src" / "lib"
    (far / ".cards").mkdir(parents=True)
    write_meta(str(far / ".cards"), {"store_id": "st_far"})
    cid = origin.import_id("lib", "topic")
    copy = {"id": cid, "provenance": {"imported_from": "lib"}}
    got = origin.exported_origin(copy, "st_src", tmp_path / "src", ".cards")
    assert got == origin.Origin("st_far", "topic", "lib")
    # With another folder name there is no identity to find, so the digest of the path stands in.
    other = origin.exported_origin(copy, "st_src", tmp_path / "src", ".elsewhere")
    assert other.store.startswith("path:") and other.id == "topic"
    # An original is its own origin; a copy that lost its provenance is nobody's original.
    assert origin.exported_origin({"id": "topic"}, "st_src", Path("."), ".cards") == origin.Origin("st_src", "topic", ".")
    assert origin.exported_origin({"id": "x--y"}, "st_src", Path("."), ".cards") is None


def test_choose_imports_keeps_one_copy_per_id_and_per_file_set():
    def item(cid, files, hops=0):
        return {"id": cid, "files": files, "hops": hops, "origin_fields": {origin.ORIGIN_ROOT: "."}}
    offered = [item("a", ["f.py"], hops=1), item("a", ["f.py"], hops=0), item("b", ["f.py"]), item("c", ["g.py"])]
    kept = origin.choose_imports(offered, own_cards=[])
    assert sorted(i["id"] for i in kept) == ["a", "c"]
    skipped = []
    assert origin.choose_imports([item("d", ["own.py"])], [{"id": "own", "files": ["own.py"]}], skipped) == []
    assert [i["id"] for i in skipped] == ["d"]


def test_created_at_is_stamped_once_and_never_invented_for_an_undated_card():
    fresh = {"id": "c"}
    origin.stamp_created_at(fresh, None)
    stamp = fresh["provenance"]["created_at"]
    again = {"id": "c", "provenance": {}}
    origin.stamp_created_at(again, {"provenance": {"created_at": stamp}})
    assert again["provenance"]["created_at"] == stamp
    undated = {"id": "c"}
    origin.stamp_created_at(undated, {"id": "c", "provenance": {}})
    assert "created_at" not in undated["provenance"]
