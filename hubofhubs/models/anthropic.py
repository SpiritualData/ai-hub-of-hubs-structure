"""AnthropicProvider: plan (one forced-tool call), answer, web search through the native server tool, and the live model list.
Needs the ``anthropic`` extra, imported on first use. Settings are constructor arguments; the key is never read from the environment."""
import inspect
from typing import Any, Dict, List, Optional

from esoi import implementation

from ..ports.model import ModelProviderBase
from .family import is_family_name, resolve_model_name
from .layers import blocks_to_prompt, cache_control_indices
from .listing import ModelListCache
from .retry import retry_transient
from .. import arm_needs as needs


def build_cached_system(system: Optional[str], layers: List[Dict[str, Any]]) -> tuple:
    """Prompt-layer blocks as an Anthropic ``system`` array plus the volatile tail text, ``(system_array, tail_text)``.

    The ``cache=True`` blocks become system text blocks, those chosen by ``cache_control_indices`` carrying an ephemeral
    breakpoint (capped at the vendor limit of four). A plain ``system`` string rides first, uncached. The single ``cache=False``
    tail becomes the user turn."""
    cached = [b for b in (layers or []) if b.get("cache")]
    breakpoints = set(cache_control_indices(cached))
    system_array: List[Dict[str, Any]] = [{"type": "text", "text": system}] if system and system.strip() else []
    for i, block in enumerate(cached):
        entry: Dict[str, Any] = {"type": "text", "text": str(block.get("text") or "")}
        if i in breakpoints:
            entry["cache_control"] = {"type": "ephemeral"}
        system_array.append(entry)
    return system_array, blocks_to_prompt([b for b in (layers or []) if not b.get("cache")])


def thinking_kwargs(create, enabled: bool = False) -> Dict[str, Any]:
    """Request kwargs that turn extended thinking off for one ``messages.create``. Reasoning models spend ``max_tokens`` on a
    thinking block before any text, so a bounded call can return no text and take several times longer. Empty when ``enabled`` or
    when the installed SDK's ``create`` has no ``thinking`` parameter."""
    if enabled:
        return {}
    try:
        return {"thinking": {"type": "disabled"}} if "thinking" in inspect.signature(create).parameters else {}
    except (TypeError, ValueError):
        return {}


@implementation("call-a-model", "anthropic")
class AnthropicProvider(ModelProviderBase):
    REQUIRES = (needs.ANTHROPIC_API, needs.ANTHROPIC_SDK)

    def __init__(self, *, api_key: Optional[str] = None, cache_seconds: float = 3600.0, max_answer_tokens: int = 2048,
                 max_plan_tokens: int = 800, thinking: bool = False,
                 env_name: Optional[str] = None):
        super().__init__()
        self.api_key = api_key
        self.env_name = env_name           # the consumer's name for where the key comes from, so a missing key can name it
        self.max_answer_tokens = max_answer_tokens
        self.max_plan_tokens = max_plan_tokens
        self.thinking = thinking
        self.client = None
        self.listing = ModelListCache(cache_seconds)

    def get_client(self):
        if self.client is None:
            import anthropic  # lazy: the anthropic extra
            if not self.api_key:
                raise RuntimeError(f"{self.env_name} is not configured" if self.env_name else "an Anthropic API key is not configured")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        return self.client

    def create(self, **kwargs) -> Any:
        """One ``messages.create`` with thinking off (unless enabled), counting the call and its tokens."""
        client = self.get_client()
        self.call_count += 1
        resp = client.messages.create(**kwargs, **thinking_kwargs(client.messages.create, self.thinking))
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.tokens_in += getattr(usage, "input_tokens", 0) or 0
            self.tokens_out += getattr(usage, "output_tokens", 0) or 0
        return resp

    @retry_transient(max_retries=3, base_delay=1.0)
    def resolve_model(self, model: str) -> str:
        """A bare family name ("sonnet", "claude-opus") becomes the newest live id of that family; a concrete id passes through."""
        return resolve_model_name(model, self.list_models()) if is_family_name(model) else model

    def plan(self, prompt: str, *, model: str, tool_schema: Dict[str, Any],
             layers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        self.get_client()      # first: a missing key or library raises here, so a router can fail over
        kwargs: Dict[str, Any] = {"model": self.resolve_model(model), "max_tokens": self.max_plan_tokens, "tools": [tool_schema],
                                  "tool_choice": {"type": "tool", "name": tool_schema["name"]}}
        system_array, tail = build_cached_system(None, layers) if layers else ([], prompt)
        if system_array:
            kwargs["system"] = system_array
        kwargs["messages"] = [{"role": "user", "content": tail}]
        for block in self.create(**kwargs).content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_schema["name"]:
                return dict(block.input or {})
        raise RuntimeError("planner returned no structured decision")

    @retry_transient(max_retries=3, base_delay=1.0)
    def answer(self, messages: List[Dict[str, Any]], *, model: str, system: Optional[str] = None,
               layers: Optional[List[Dict[str, Any]]] = None) -> str:
        """With ``layers``, the cacheable head and context are the ``system`` array and the tail is the one user turn; otherwise
        ``messages`` pass through unflattened (a content may be a list of text and image blocks)."""
        kwargs: Dict[str, Any] = {"model": self.resolve_model(model), "max_tokens": self.max_answer_tokens}
        if layers:
            system_array, tail = build_cached_system(system, layers)
            kwargs["messages"] = [{"role": "user", "content": tail}]
            if system_array:
                kwargs["system"] = system_array
        else:
            kwargs["messages"] = messages
            if system:
                kwargs["system"] = system
        resp = self.create(**kwargs)
        return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")

    def supports_web_search(self, model: Optional[str] = None) -> bool:
        return bool(self.api_key)

    @retry_transient(max_retries=3, base_delay=1.0)
    def web_search(self, query: str, *, model: str, max_results: int = 5, instruction: Optional[str] = None) -> Dict[str, Any]:
        """Search through Claude's native web_search server tool (no extra key):
        ``{"answer", "results": [{title, url, snippet, passages, passage_kind, date}]}``. ``passages`` are each page's distinct
        ``cited_text`` (verbatim from the page, ``passage_kind`` "verbatim"); ``snippet`` is the first; ``date`` is the result's
        ``page_age`` when the tool gives one. ``max_results`` also caps the server-side searches (``max_uses``, 1 to 5).
        ``instruction`` is put before the query."""
        resp = self.create(model=self.resolve_model(model), max_tokens=self.max_answer_tokens,
                           tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max(1, min(int(max_results), 5))}],
                           messages=[{"role": "user", "content": f"{instruction.strip()}\n\n{query}" if instruction and instruction.strip() else query}])
        parts: List[str] = []
        results: List[Dict[str, Any]] = []

        def add(title: str, url: str, snippet: str = "", date: str = "") -> None:
            if not url:
                return
            row = next((r for r in results if r["url"] == url), None)
            if row is None:
                row = {"title": title or "", "url": url, "snippet": "", "passages": [], "passage_kind": "", "date": ""}
                results.append(row)
            row["title"] = row["title"] or title or ""
            row["date"] = row["date"] or date or ""
            if snippet and snippet not in row["passages"]:
                row["passages"].append(snippet)
                row["snippet"] = row["passages"][0]
                row["passage_kind"] = "verbatim"

        for block in resp.content:
            kind = getattr(block, "type", None)
            if kind == "text":
                parts.append(getattr(block, "text", "") or "")
                for cit in (getattr(block, "citations", None) or []):
                    add(getattr(cit, "title", ""), getattr(cit, "url", ""), getattr(cit, "cited_text", ""))
            elif kind == "web_search_tool_result":
                for r in (getattr(block, "content", None) or []):
                    if getattr(r, "type", None) == "web_search_result":
                        add(getattr(r, "title", ""), getattr(r, "url", ""), "", getattr(r, "page_age", "") or "")
        return {"answer": "".join(parts), "results": results[:max_results]}

    @retry_transient(max_retries=2, base_delay=1.0)
    def fetch_models(self) -> List[str]:
        page = self.get_client().models.list()       # already latest-first
        return [m.id for m in getattr(page, "data", []) if getattr(m, "id", None)]

    def list_models(self) -> List[str]:
        return self.listing.get(self.fetch_models)
