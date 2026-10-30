"""A card store has an identity that outlives its location; the hub names no consumer folder or collection."""
import pytest

from hubofhubs.recall import card_store_identity as ident
from hubofhubs.recall.card_repository import FilesystemCardRepository


def test_a_store_without_a_meta_gets_no_bare_identity(tmp_path):
    assert ident.ensure_store_id(str(tmp_path)) is None
    assert not (tmp_path / ident.BOOTSTRAP_META_FILE).exists()


def test_a_new_store_is_qualified_and_an_existing_meta_stays_legacy(tmp_path):
    fresh = ident.identity_of({}, root="/corpus")
    assert fresh["vector_id_scheme"] == ident.SCHEME_QUALIFIED and fresh["root"] == "/corpus"
    older = ident.identity_of({"version": 3})
    assert older["vector_id_scheme"] == ident.SCHEME_LEGACY and older["store_id"].startswith("st_")


def test_identity_survives_a_rewrite_and_a_root_move_is_recorded(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    new_root = tmp_path / "moved"
    new_root.mkdir()
    ident.write_meta(str(cards), {"version": 1, **ident.identity_of({"version": 1}, root=str(tmp_path))})
    before = ident.store_id_of(str(cards))
    assert before and ident.ensure_store_id(str(cards)) == before
    plan = ident.apply_move_root(str(cards), str(new_root))
    assert plan.ok and plan.reembeds == 0 and ident.read_meta(str(cards))["root"] == str(new_root)
    assert ident.read_meta(str(cards))["root_history"][-1]["root"] == str(tmp_path)
    assert ident.store_id_of(str(cards)) == before


def test_a_move_to_a_missing_root_is_refused_unless_forced(tmp_path):
    ident.write_meta(str(tmp_path), {"store_id": "st_x"})
    plan = ident.apply_move_root(str(tmp_path), str(tmp_path / "nope"))
    assert not plan.ok and "root" not in ident.read_meta(str(tmp_path))
    assert ident.apply_move_root(str(tmp_path), str(tmp_path / "nope"), force=True).new_root.endswith("nope")


def test_the_derived_origin_is_deterministic_and_root_specific(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    assert ident.derived_origin("h", str(one)) == ident.derived_origin("h", str(one))
    assert ident.derived_origin("h", str(one)) != ident.derived_origin("h", str(two))
    assert ident.derived_origin("h", str(one)) != ident.derived_origin("g", str(one))
    primary, accepted = ident.writer_origins(str(tmp_path / "none"), env_id="h", root=str(one))
    assert primary == ident.derived_origin("h", str(one)) and accepted == {primary}


def test_readability_names_the_reason(tmp_path):
    assert not ident.check_readable(str(tmp_path / "missing")).allowed
    assert "bootstrap_meta" in ident.check_readable(str(tmp_path)).reason
    ident.write_meta(str(tmp_path), {"store_id": "st_a"})
    assert ident.check_readable(str(tmp_path)).allowed
    ident.write_meta(str(tmp_path), {"store_id": "st_a", "merged_into": {"store_id": "st_b"}})
    assert "st_b" in ident.check_readable(str(tmp_path)).reason and ident.is_merged(str(tmp_path))


def test_the_vector_location_names_a_prefix_the_consumer_chose():
    with pytest.raises(TypeError):
        ident.vector_location_record("http://localhost")  # no default collection prefix
    rec = ident.vector_location_record("EMBEDDED", collection_prefix="mine", vector_size=8, embedder="m")
    assert rec == {"location": "embedded", "collection_prefix": "mine", "vector_size": 8, "embedder": "m"}
    assert ident.vector_location_of({"vector_location": {"location": " "}}) is None


def test_plan_move_root_counts_the_files_a_card_pins(tmp_path):
    cards, root = tmp_path / "cards", tmp_path / "root"
    root.mkdir()
    (root / "a.py").write_text("x")
    FilesystemCardRepository(str(cards)).write("c1", {"id": "c1", "files": [{"path": "a.py"}, "b.py"]})
    ident.write_meta(str(cards), {"store_id": "st_a"})
    plan = ident.plan_move_root(str(cards), str(root))
    assert (plan.card_count, plan.file_refs, plan.refs_present_at_new_root, plan.missing_samples) == (1, 2, 1, ["b.py"])
