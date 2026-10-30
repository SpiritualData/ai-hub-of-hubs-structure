"""Deterministic URL detection: the links in a message, found by pattern, and what each one is, from its address alone."""
from hubofhubs.critique.link_detect import describe_link, extract_urls

ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"


def test_extract_urls_handles_prose_markdown_and_duplicates():
    msg = (f"Please read https://docs.google.com/document/d/{ID}/edit, and also "
           "(https://example.org/a.pdf). See [the site](https://example.org/x?y=1). "
           "https://example.org/a.pdf again. Wiki: https://en.wikipedia.org/wiki/Foo_(bar).")
    assert extract_urls(msg) == [
        f"https://docs.google.com/document/d/{ID}/edit",
        "https://example.org/a.pdf",
        "https://example.org/x?y=1",
        "https://en.wikipedia.org/wiki/Foo_(bar)",
    ]


def test_extract_urls_none_and_junk():
    assert extract_urls("") == [] and extract_urls(None) == [] and extract_urls("no links here") == []
    assert extract_urls("see http:// nothing") == []


def test_describe_link():
    assert describe_link(f"https://docs.google.com/spreadsheets/d/{ID}/edit") == "Google Sheet"
    assert describe_link(f"https://docs.google.com/document/d/{ID}/edit") == "Google Doc"
    assert describe_link(f"https://docs.google.com/presentation/d/{ID}/edit") == "Google Slides"
    assert describe_link(f"https://drive.google.com/file/d/{ID}/view") == "Google Drive file"
