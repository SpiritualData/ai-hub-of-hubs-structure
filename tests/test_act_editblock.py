"""SEARCH/REPLACE and whole-file edit parsing, and content-anchored application, with no filesystem and no network."""
from hubofhubs.act import editblock


def test_a_search_replace_block_is_parsed_with_its_filename():
    msg = "notes.md\n```\n<<<<<<< SEARCH\nhello\n=======\nworld\n>>>>>>> REPLACE\n```\n"
    assert list(editblock.find_original_update_blocks(msg)) == [("notes.md", "hello\n", "world\n")]


def test_apply_edit_replaces_the_matching_chunk():
    assert editblock.apply_edit("hello\nbye\n", "hello", "world") == "world\nbye\n"


def test_apply_edit_tolerates_a_uniform_indent_drift():
    assert editblock.apply_edit("  hello\nbye\n", "hello\n", "world\n") == "  world\nbye\n"


def test_apply_edit_returns_none_when_the_search_text_is_absent():
    assert editblock.apply_edit("abc\n", "zzz", "y") is None


def test_an_empty_search_creates_or_appends():
    assert editblock.apply_edit(None, "", "new\n") == "new\n"
    assert editblock.apply_edit("old\n", "", "more\n") == "old\nmore\n"
    assert editblock.apply_edit(None, "something", "x") is None


def test_whole_file_blocks_yield_filename_and_new_content():
    assert list(editblock.find_whole_file_blocks("a.txt\n```\nfull\n```\n")) == [("a.txt", "full\n")]
