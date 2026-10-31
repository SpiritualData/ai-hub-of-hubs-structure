"""The provider arm: a model provider's own web search tool, here the hub's Gemini provider (the only hub provider with one).

The OpenAI provider in the hub has no native web search, so an OpenAI provider arm is not measured (nothing to call)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from search_backend.score import NoCredential, TOP, priced  # noqa: E402

MODEL = "gemini-2.5-flash-lite"


class CountingProvider:
    """Adds the token counters ``priced`` reads around the provider's ``web_search`` (Gemini keeps its own usage totals)."""
    model = MODEL

    def __init__(self, provider):
        self.provider = provider
        self.tokens_in = self.tokens_out = 0

    def search(self, query, **kwargs):
        from hubofhubs.websearch.backends import ProviderNativeBackend
        before = (self.provider.tokens_in, self.provider.tokens_out)
        try:
            return ProviderNativeBackend(self.provider, MODEL).search(query, **kwargs)
        finally:
            self.tokens_in += self.provider.tokens_in - before[0]
            self.tokens_out += self.provider.tokens_out - before[1]


def build(meter):
    key = next((os.environ[n] for n in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY") if os.environ.get(n)), "")
    if not key:
        raise NoCredential("not measured: no credential (GEMINI_API_KEY, GOOGLE_API_KEY or GOOGLE_AI_API_KEY is not set)")
    from hubofhubs.models.gemini import GeminiProvider
    backend = priced(CountingProvider(GeminiProvider(api_key=key)), meter)
    return lambda kind, args: [(h.url, h.title) for h in backend.search(args["question"], max_results=TOP).hits[:TOP]]
