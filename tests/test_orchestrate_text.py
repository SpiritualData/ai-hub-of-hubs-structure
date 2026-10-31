"""Status-line text helpers cut on sensible boundaries."""
from hubofhubs.orchestrate.text import clip_head_and_tail, ellipsize, sentence


def test_ellipsize_leaves_short_text_and_collapses_whitespace():
    assert ellipsize("a  b\n c", 20) == "a b c"


def test_ellipsize_cuts_at_a_word_and_drops_the_punctuation_it_leaves():
    out = ellipsize("alpha beta, gamma delta epsilon", 14)
    assert out == "alpha beta…" and len(out) <= 14


def test_ellipsize_cuts_inside_a_long_word_when_no_space_is_near():
    assert ellipsize("x" * 50, 10) == "x" * 9 + "…"


def test_a_status_sentence_ends_in_a_full_stop_unless_it_already_ends_in_closing_punctuation():
    assert sentence("Done") == "Done."
    assert sentence("Done?") == "Done?" and sentence("Wait…") == "Wait…" and sentence("") == ""


def test_clip_head_and_tail_keeps_both_ends():
    text = "H" * 200 + "T" * 200
    out = clip_head_and_tail(text, 100)
    assert out.startswith("H" * 40) and out.endswith("T" * 60) and "[...]" in out
    assert clip_head_and_tail("short", 100) == "short"
