"""Bootstrap settings arrive as arguments (the hub reads no environment), and the extractors stay bounded."""
import json

from hubofhubs.recall.context_bootstrap_support import (
    _BOOTSTRAP_MAX_BYTES,
    _BOOTSTRAP_WORKERS_DEFAULT,
    _read_bootstrap_meta,
    _write_bootstrap_meta,
    bootstrap_workers,
    flag_enabled,
    optional_positive_int,
)
from hubofhubs.recall.context_card_ceilings import positive_int


def test_workers_take_the_first_integer_setting_in_order_of_strength():
    assert bootstrap_workers([("STAGE", ""), ("BUDGET", "3")]) == 3
    assert bootstrap_workers([("STAGE", "2"), ("BUDGET", "3")]) == 2
    assert bootstrap_workers() == _BOOTSTRAP_WORKERS_DEFAULT


def test_a_garbage_worker_setting_is_skipped_and_never_zero():
    assert bootstrap_workers([("STAGE", "not-a-number")]) == _BOOTSTRAP_WORKERS_DEFAULT
    assert bootstrap_workers([("STAGE", "not-a-number"), ("BUDGET", "4")]) == 4
    # A 0 would deadlock the semaphore rather than "disable" the stage.
    assert bootstrap_workers([("BUDGET", "0")]) == 1


def test_optional_ceilings_default_to_no_limit():
    assert optional_positive_int("X", None) is None
    assert optional_positive_int("X", "") is None
    assert optional_positive_int("X", "12") == 12
    assert optional_positive_int("X", "0") is None
    assert optional_positive_int("X", "-3") is None
    assert optional_positive_int("X", "lots") is None


def test_flags_are_on_unless_switched_off():
    assert flag_enabled(None) and flag_enabled("") and flag_enabled("1") and flag_enabled("yes")
    assert not flag_enabled("0") and not flag_enabled("False") and not flag_enabled(" no ")
    assert flag_enabled("", default=True) and not flag_enabled("", default=False)


def test_a_per_folder_cap_keeps_zero_as_no_cap_and_garbage_as_the_default():
    assert positive_int("X", "0", 8) == 0
    assert positive_int("X", "5", 8) == 5
    assert positive_int("X", "", 8) == 8
    assert positive_int("X", "many", 8) == 8
    assert positive_int("X", "-1", 8) == 8


def test_the_meta_file_keeps_the_stores_identity_across_passes(tmp_path):
    _write_bootstrap_meta(str(tmp_path), 3, root="/corpus")
    first = _read_bootstrap_meta(str(tmp_path))
    assert first["card_count"] == 3 and first["store_id"].startswith("st_") and first["root"] == "/corpus"
    _write_bootstrap_meta(str(tmp_path), 9, root="/elsewhere")
    second = _read_bootstrap_meta(str(tmp_path))
    assert second["card_count"] == 9
    assert second["store_id"] == first["store_id"] and second["root"] == "/corpus"
    (tmp_path / "bootstrap_meta.json").write_text("{not json")
    assert _read_bootstrap_meta(str(tmp_path)) == {}


def test_head_extractors_read_a_prefix_not_the_whole_file(tmp_path):
    from hubofhubs.recall.context_card_extraction import _extract_leading_comment, _extract_text_description, _read_head

    # A corpus root can legitimately contain data dumps no name-based ignore rule excludes. These
    # two extractors only ever inspect the TOP of a file, so their cost must not scale with its
    # size: reading one 762MB .json whole cost 6.9GB resident and OOM-killed the runner mid-task.
    marker = "MARKER_BEYOND_THE_CAP"
    big = tmp_path / "dump.json"
    big.write_text("// leading comment line\n" + ("x" * 64 + "\n") * 40_000 + marker + "\n")
    assert big.stat().st_size > 2_000_000
    assert len(_read_head(big, 8 * 1024)) <= 8 * 1024
    assert marker not in _extract_leading_comment(big)
    assert marker not in _extract_text_description(big)
    assert _read_head(tmp_path / "nope.json", 1024) == ""


def test_ast_extractors_skip_a_file_too_big_to_card(tmp_path):
    from hubofhubs.recall.context_card_extraction import _extract_symbols, _read_whole_if_small

    small = tmp_path / "small.py"
    small.write_text("def alpha():\n    pass\n\nclass Beta:\n    pass\n")
    assert "alpha" in _extract_symbols(small)
    assert _read_whole_if_small(small)

    # The AST path needs a complete source text, so oversize is SKIPPED rather than truncated --
    # a truncated module is a SyntaxError, not a smaller card. Same limit the snippet path uses.
    huge = tmp_path / "huge.py"
    huge.write_text("def gamma():\n    pass\n" + "# pad\n" * (_BOOTSTRAP_MAX_BYTES // 6))
    assert huge.stat().st_size > _BOOTSTRAP_MAX_BYTES
    assert _read_whole_if_small(huge) == ""
    assert _extract_symbols(huge) == []
