"""The DOI comparison: a DOI in a reply that no evidence of the turn holds is replaced. Offline, plain strings."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs.science.citations import PLACEHOLDER, doi_candidates, dois_in, strip_unlisted_dois, unlisted_dois  # noqa: E402

RETURNED = ("1. Easy cycling. Author One, 2021. Journal of Demos. DOI 10.5555/demo.one (https://doi.org/10.5555/demo.one). Cited by 12.\n"
            "2. Other work. DOI 10.1016/S0140-6736(20)30183-5 (https://doi.org/10.1016/S0140-6736(20)30183-5).")


def test_dois_are_read_from_bare_text_links_and_brackets_without_the_closing_punctuation():
    found = [d for _, _, d in doi_candidates("See 10.5555/Demo.One. Also [x](https://doi.org/10.1234/abc-1), and (doi:10.9999/z).")]
    assert found == ["10.5555/demo.one", "10.1234/abc-1", "10.9999/z"]
    assert [d for _, _, d in doi_candidates("10.1016/S0140-6736(20)30183-5")] == ["10.1016/s0140-6736(20)30183-5"]


def test_the_dois_a_turn_had_are_collected_from_nested_evidence():
    known = dois_in(RETURNED, {"hits": [{"doi": "10.7777/card"}]}, None)
    assert {"10.5555/demo.one", "10.1016/s0140-6736(20)30183-5", "10.7777/card"} <= known


@pytest.mark.parametrize("reply,removed", [
    ("Cycling helps (Author One 2021, DOI 10.5555/demo.one).", []),
    ("Cycling helps ([paper](https://doi.org/10.5555/demo.one)).", []),
    ("Cycling helps, see 10.5555/DEMO.ONE.", []),                                   # case does not matter
    ("Also 10.1016/S0140-6736(20)30183-5.", []),
    ("Invented: DOI 10.5555/made.up and DOI 10.5555/demo.one.", ["10.5555/made.up"]),
    ("A truncated copy 10.5555/demo is not the returned one.", ["10.5555/demo"]),
    ("Two invented 10.1111/aaa; 10.2222/bbb and 10.1111/aaa again", ["10.1111/aaa", "10.2222/bbb"]),
    ("No identifiers here, only the claim.", []),
])
def test_only_dois_the_turn_did_not_have_are_listed(reply, removed):
    assert unlisted_dois(reply, dois_in(RETURNED)) == removed


def test_an_unknown_doi_is_replaced_and_the_rest_of_the_reply_is_untouched():
    reply = "Study A (DOI 10.5555/made.up) agrees with study B (DOI 10.5555/demo.one)."
    text, removed = strip_unlisted_dois(reply, dois_in(RETURNED))
    assert removed == ["10.5555/made.up"]
    assert text == f"Study A (DOI {PLACEHOLDER}) agrees with study B (DOI 10.5555/demo.one)."


def test_with_no_evidence_every_doi_is_replaced_failing_closed():
    text, removed = strip_unlisted_dois("DOI 10.5555/demo.one", [])
    assert removed == ["10.5555/demo.one"] and "10.5555" not in text
