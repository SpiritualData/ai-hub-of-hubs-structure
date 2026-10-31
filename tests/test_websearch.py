"""The search-backend seat executes: arms resolve by name, assemble builds them from options, and no test touches a network."""
import pytest

import hubofhubs
from hubofhubs import AssemblyConfig, AssemblyError, assemble, names
from hubofhubs.ports.search import SearchBackendError
from hubofhubs.websearch.backends import FallbackSearchBackend, load_file_specs

ARMS = ["brave", "gemini", "provider", "searxng", "serper", "tavily"]


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


def fake_http(body):
    calls = []

    def call(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse(body)
    call.calls = calls
    return call


def test_the_hub_lists_every_search_arm_by_name():
    assert names("search-backend") == ARMS


def test_assemble_builds_the_selected_arm_from_options_and_searches_through_it():
    http = fake_http({"results": [{"title": "T", "url": "https://x.invalid", "content": "body"}]})
    config = AssemblyConfig(solutions=("search-backend",), selections={"search-backend": "searxng"},
                       options={"search-backend": {"base_url": "http://searx.invalid/", "http": http}})
    system = assemble(config)
    response = system["search-backend"].search("a question", max_results=3)
    assert [(h.title, h.url, h.snippet) for h in response.hits] == [("T", "https://x.invalid", "body")]
    assert http.calls[0][:2] == ("GET", "http://searx.invalid/search")
    assert system.reasons[0].startswith("search-backend -> searxng (layer: consumer selections")


def test_a_data_described_api_arm_sends_the_key_and_reads_the_fields():
    http = fake_http({"organic": [{"title": "T", "link": "https://x.invalid", "snippet": "s"}]})
    arm = hubofhubs.resolve("search-backend", "serper")("k1", http)
    assert arm.search("q").hits[0].url == "https://x.invalid"
    method, url, kwargs = http.calls[0]
    assert (method, kwargs["headers"]["X-API-KEY"], kwargs["json"]) == ("POST", "k1", {"q": "q", "num": 5})


def test_the_search_seat_default_is_the_metric_recorded_selection():
    system = assemble(AssemblyConfig(solutions=("search-backend",)))
    assert system.reasons[0].startswith("search-backend -> gemini (layer: hubofhubs default")


def test_a_seat_with_no_selected_arm_names_the_remedy():
    with pytest.raises(AssemblyError, match="remedy"):
        assemble(AssemblyConfig(solutions=("context-assembler",)))


def test_a_failing_arm_raises_the_seat_error_and_a_chain_moves_on():
    class Down:
        name = "down"

        def search(self, query, *, max_results=5):
            raise SearchBackendError("down: HTTP 500", status_code=500)

    class Up:
        name = "up"

        def search(self, query, *, max_results=5):
            return hubofhubs.websearch.backends.SearchResponse(hits=[hubofhubs.websearch.backends.SearchHit("t", "u")])

    assert FallbackSearchBackend([Down(), Up()]).search("q").hits[0].url == "u"
    with pytest.raises(SearchBackendError, match="HTTP 500"):
        FallbackSearchBackend([Down()]).search("q")


def test_a_missing_library_names_the_extra_to_install(monkeypatch):
    import builtins
    real = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError(name)
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse)
    with pytest.raises(SearchBackendError, match=r"hubofhubs\[web\]"):
        hubofhubs.websearch.backends.default_http("GET", "http://x.invalid")


def test_a_bad_apis_file_loads_nothing(tmp_path):
    path = tmp_path / "apis.json"
    path.write_text("not json")
    assert load_file_specs(str(path)) == {}
