"""Passages, passage kind, date and the caller's instruction on the search-backend seat, from recorded fixtures (no network)."""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from hubofhubs.ports.search import SearchHit
from hubofhubs.seats import SearchBackend
from hubofhubs.websearch.backends import (
    BraveBackend, FallbackSearchBackend, ProviderNativeBackend, SearxngBackend, SerperBackend, TavilyBackend,
)
from hubofhubs.websearch.gemini import GeminiGroundingBackend


class Reply:
    def __init__(self, body: Dict[str, Any]):
        self.status_code, self.headers, self.body = 200, {}, body

    def json(self):
        return self.body


def serving(body):
    return lambda method, url, **kwargs: Reply(body)


def test_hit_defaults_keep_old_construction_working():
    hit = SearchHit("t", "https://a.example/x", "s", "2024")
    assert (hit.passages, hit.passage_kind, hit.snippet, hit.date) == ((), "", "s", "2024")


def test_protocol_and_every_arm_take_instruction():
    assert "instruction" in inspect.signature(SearchBackend.search).parameters
    for arm in (SerperBackend, BraveBackend, TavilyBackend, SearxngBackend, ProviderNativeBackend, GeminiGroundingBackend,
                FallbackSearchBackend):
        assert "instruction" in inspect.signature(arm.search).parameters, arm


@pytest.mark.parametrize("backend,body,date", [
    (SerperBackend, {"organic": [{"title": "T", "link": "https://a.example/p", "snippet": "Excerpt one.", "date": "Jan 1, 2024"}]}, "Jan 1, 2024"),
    (BraveBackend, {"web": {"results": [{"title": "T", "url": "https://a.example/p", "description": "Excerpt <b>one</b>.", "age": "2 days ago"}]}}, "2 days ago"),
    (TavilyBackend, {"results": [{"title": "T", "url": "https://a.example/p", "content": "Excerpt one.", "published_date": "2024-01-01"}]}, "2024-01-01"),
])
def test_snippet_apis_give_one_snippet_passage_and_their_date(backend, body, date):
    resp = backend(api_key="k", http=serving(body)).search("q", instruction="ignored by a search API")
    hit = resp.hits[0]
    assert hit.passage_kind == "snippet"
    assert hit.passages == (hit.snippet,) and "Excerpt" in hit.snippet
    assert hit.date == date


def test_searxng_snippet_passage_and_published_date():
    body = {"results": [{"title": "T", "url": "https://a.example/p", "content": "Excerpt.", "publishedDate": "2023-05-05"}]}
    hit = SearxngBackend(base_url="http://x", http=serving(body)).search("q", instruction="i").hits[0]
    assert (hit.passages, hit.passage_kind, hit.date) == (("Excerpt.",), "snippet", "2023-05-05")


def test_snippet_api_hit_without_snippet_has_no_kind():
    body = {"organic": [{"title": "T", "link": "https://a.example/p"}]}
    hit = SerperBackend(api_key="k", http=serving(body)).search("q").hits[0]
    assert (hit.passages, hit.passage_kind) == ((), "")


class RecordedModels:
    def __init__(self, response):
        self.response, self.prompts = response, []

    def generate_content(self, *, model, contents, config):
        self.prompts.append(contents)
        return self.response


def gemini_recording():
    """Two pages; page 0 has three supports (one repeated), page 1 has one long support."""
    long_text = "word " * 120
    chunks = [SimpleNamespace(web=SimpleNamespace(uri="https://g.example/r0", title="a.example")),
              SimpleNamespace(web=SimpleNamespace(uri="https://g.example/r1", title="b.example"))]
    supports = [SimpleNamespace(segment=SimpleNamespace(text="First claim."), grounding_chunk_indices=[0]),
                SimpleNamespace(segment=SimpleNamespace(text="Second claim."), grounding_chunk_indices=[0, 1]),
                SimpleNamespace(segment=SimpleNamespace(text="First claim."), grounding_chunk_indices=[0]),
                SimpleNamespace(segment=SimpleNamespace(text=long_text.strip()), grounding_chunk_indices=[1])]
    meta = SimpleNamespace(grounding_chunks=chunks, grounding_supports=supports, web_search_queries=["q"])
    return SimpleNamespace(text="Answer.", usage_metadata=None, candidates=[SimpleNamespace(grounding_metadata=meta)])


def test_gemini_passages_are_separate_uncapped_attributed_and_snippet_is_unchanged():
    client = SimpleNamespace(models=RecordedModels(gemini_recording()))
    backend = GeminiGroundingBackend(api_key="k", client=client, http=lambda *a, **k: Reply({}))
    hits = {h.title: h for h in backend.search("q").hits}
    a, b = hits["a.example"], hits["b.example"]
    assert a.passages == ("First claim.", "Second claim.")
    assert a.snippet == "First claim. Second claim."
    assert b.passages[0] == "Second claim." and len(b.passages[1]) > 300 and len(b.snippet) <= 303
    assert a.passage_kind == b.passage_kind == "attributed"
    assert a.date == ""            # the grounding API exposes no page date


def test_gemini_instruction_reaches_the_prompt_only_when_given():
    models = RecordedModels(gemini_recording())
    backend = GeminiGroundingBackend(api_key="k", client=SimpleNamespace(models=models), http=lambda *a, **k: Reply({}))
    backend.search("the claim")
    backend.search("the claim", instruction="include facts that count against the claim")
    assert "count against" not in models.prompts[0]
    assert "include facts that count against the claim" in models.prompts[1] and "the claim" in models.prompts[1]


def test_provider_native_passes_kind_passages_date_and_instruction():
    seen = {}

    class Provider:
        def web_search(self, query, *, model, max_results, instruction=None):
            seen["instruction"] = instruction
            return {"answer": "a", "results": [{"title": "T", "url": "https://a.example/p", "snippet": "One.",
                                                "passages": ["One.", "Two."], "passage_kind": "verbatim", "date": "May 1, 2025"}]}

    hit = ProviderNativeBackend(Provider(), "m").search("q", instruction="be adversarial").hits[0]
    assert seen["instruction"] == "be adversarial"
    assert (hit.passages, hit.passage_kind, hit.date, hit.snippet) == (("One.", "Two."), "verbatim", "May 1, 2025", "One.")


def test_provider_native_keeps_working_with_a_provider_that_has_no_instruction_keyword():
    class OldProvider:
        def web_search(self, query, *, model, max_results):
            return {"answer": "", "results": [{"title": "T", "url": "https://a.example/p", "snippet": "S"}]}

    hit = ProviderNativeBackend(OldProvider(), "m").search("q").hits[0]
    assert (hit.snippet, hit.passages, hit.passage_kind) == ("S", (), "")
    with pytest.raises(Exception):      # an instruction the provider cannot take is an error, not silently dropped
        ProviderNativeBackend(OldProvider(), "m").search("q", instruction="x")


def anthropic_recording():
    """A recorded Anthropic web_search reply: results first (with page_age), then cited text blocks (two quotes for page 1)."""
    def result(title, url, age):
        return SimpleNamespace(type="web_search_result", title=title, url=url, page_age=age)

    def cite(title, url, text):
        return SimpleNamespace(type="web_search_result_location", title=title, url=url, cited_text=text)

    return SimpleNamespace(content=[
        SimpleNamespace(type="web_search_tool_result", content=[result("P1", "https://a.example/1", "April 30, 2025"),
                                                                result("P2", "https://b.example/2", None)]),
        SimpleNamespace(type="text", text="Claim one. ", citations=[cite("P1", "https://a.example/1", "Verbatim quote A.")]),
        SimpleNamespace(type="text", text="Claim two.", citations=[cite("P1", "https://a.example/1", "Verbatim quote B."),
                                                                   cite("P1", "https://a.example/1", "Verbatim quote A.")]),
    ])


def test_anthropic_provider_gives_verbatim_passages_and_page_age_and_takes_instruction():
    pytest.importorskip("anthropic")
    from hubofhubs.models.anthropic import AnthropicProvider
    provider = object.__new__(AnthropicProvider)
    sent = []
    provider.create = lambda **kw: (sent.append(kw), anthropic_recording())[1]
    provider.resolve_model = lambda m: m
    provider.max_answer_tokens = 100
    result = provider.web_search("q", model="m", instruction="include counter-evidence")
    assert sent[0]["messages"][0]["content"].startswith("include counter-evidence")
    first, second = result["results"]
    assert first["passages"] == ["Verbatim quote A.", "Verbatim quote B."]
    assert first["snippet"] == "Verbatim quote A." and first["passage_kind"] == "verbatim" and first["date"] == "April 30, 2025"
    assert (second["passages"], second["passage_kind"], second["date"]) == ([], "", "")
    hit = ProviderNativeBackend(provider, "m").search("q").hits[0]
    assert hit.passages == ("Verbatim quote A.", "Verbatim quote B.") and hit.passage_kind == "verbatim"


def test_gemini_provider_supports_become_attributed_passages_without_a_date():
    pytest.importorskip("google.genai")
    from hubofhubs.models.gemini import GeminiProvider
    provider = object.__new__(GeminiProvider)
    prompts = []
    provider.request = lambda model, contents, config, *rest: (prompts.append(contents), gemini_recording())[1]
    provider.resolve_model = lambda m: m
    rows = provider.web_search("q", model="m", instruction="include counter-evidence")["results"]
    assert prompts[0].startswith("include counter-evidence")
    assert rows[0]["passages"] == ["First claim.", "Second claim."] and rows[0]["passage_kind"] == "attributed"
    assert rows[0]["date"] == ""
