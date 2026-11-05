"""A blocked network is not an answer: the scholarly arms let esoi's offline guard refusal through instead of turning it into a
typed 'network' error, so the entry check classifies the call as a live attempt and never counts it ok. No test reaches the network."""
import sys
from pathlib import Path

import httpx
import pytest
from esoi import entry

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from hubofhubs.the_world.science import crossref  # noqa: E402
from hubofhubs.the_world.science.openalex import OpenAlexWorks  # noqa: E402
from hubofhubs.the_world.science.transport import default_transport, guard_in  # noqa: E402


def refuse(*args, **kwargs):
    raise entry.Offline("blocked")


def refused_inside_httpx(*args, **kwargs):
    try:
        raise entry.Offline("blocked")
    except entry.Offline as inner:
        raise httpx.ConnectError("connect failed") from inner


def test_the_guard_is_found_through_a_wrapped_cause():
    try:
        refused_inside_httpx()
    except httpx.ConnectError as exc:
        assert isinstance(guard_in(exc), entry.Offline)
    assert guard_in(httpx.ConnectError("plain")) is None


def test_default_transport_reraises_the_guard_but_wraps_a_real_network_failure(monkeypatch):
    monkeypatch.setattr(httpx, "get", refused_inside_httpx)
    with pytest.raises(entry.Offline):
        default_transport("https://example.invalid", params={}, headers={}, timeout=1)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    from hubofhubs.the_world.science.transport import TransportError
    with pytest.raises(TransportError) as raised:
        default_transport("https://example.invalid", params={}, headers={}, timeout=1)
    assert raised.value.kind == "network"


def test_openalex_search_does_not_swallow_the_guard():
    with pytest.raises(entry.Offline):
        OpenAlexWorks(transport=refuse).search("meditation")


def test_a_custom_transport_failure_is_still_a_typed_error():
    def broken(*args, **kwargs):
        raise OSError("down")
    observation = OpenAlexWorks(transport=broken).search("meditation")
    assert observation.kind == "error" and "network" in str(observation.error)


def test_crossref_does_not_swallow_the_guard():
    with pytest.raises(entry.Offline):
        crossref.lookup_doi("10.1000/xyz", transport=refuse)


def test_the_entry_check_never_counts_know_the_world_ok():
    import subprocess
    root = Path(__file__).resolve().parents[4]
    done = subprocess.run([sys.executable, "-m", "esoi.runtime.assemble_by_name.entry_cli"], cwd=root, capture_output=True, text=True, timeout=240)
    line = [one for one in done.stdout.splitlines() if "the-science" in one and one.startswith(("ok", "live", "pending"))]
    assert line and not line[0].startswith("ok"), done.stdout[-600:]
