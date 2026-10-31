"""GeminiProvider: plan (forced JSON), answer (with native system_instruction when prompt layers are given), web search through
Google Search grounding, URL fetch through url_context, and the live model list. Needs the ``gemini`` extra (``google-genai``),
imported on first use. The key is a constructor argument; nothing is read from the environment."""
import logging
from typing import Any, Dict, List, Optional

from esoi import implementation

from ..ports.model import ModelProviderBase
from .family import is_family_name, resolve_model_name
from .layers import join_layers
from .listing import ModelListCache
from .retry import parse_json_with_retry, retry_transient

log = logging.getLogger("hubofhubs.models.gemini")
FALLBACK_MODELS = ("gemini-2.0-flash", "gemini-1.5-pro")


def split_layers_for_gemini(system: Optional[str], layers: List[Dict[str, Any]]) -> tuple:
    """Prompt-layer blocks as Gemini's ``(system_instruction, contents)``. Implicit caching keys on a stable system instruction
    plus a stable contents prefix, so the first (cache) block is the instruction and the rest are joined in order into
    ``contents``. A plain ``system`` string is prepended to the instruction, which is None when there is no head."""
    rest = list(layers or [])
    head = str(rest.pop(0).get("text") or "") if rest and rest[0].get("cache") else ""
    instruction = "\n\n".join(p for p in ((system or "").strip(), head) if p) or None
    return instruction, join_layers(*[str(b.get("text") or "") for b in rest])


def image_part(block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """An Anthropic-style base64 image block as a Gemini ``inline_data`` part, or None for anything else (a URL source)."""
    source = block.get("source") or {}
    if not source.get("data") or source.get("type") != "base64":
        return None
    return {"inline_data": {"mime_type": source.get("media_type") or "image/png", "data": source["data"]}}


@implementation("call-a-model", "gemini")
class GeminiProvider(ModelProviderBase):
    ENVIRON = {"api_key": ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY")}
    ENVIRON_REQUIRED = ("api_key",)

    def __init__(self, *, api_key: Optional[str] = None, cache_seconds: float = 3600.0, env_name: Optional[str] = None):
        super().__init__()
        self.api_key = api_key
        self.env_name = env_name           # the consumer's name for where the key comes from, so a missing key can name it
        self.client = None
        self.listing = ModelListCache(cache_seconds)

    def get_client(self):
        if self.client is None:
            try:
                import google.genai  # lazy: the gemini extra
            except ImportError:
                raise RuntimeError("google-genai is not installed. Install it with: pip install google-genai")
            if not self.api_key:
                raise RuntimeError(f"{self.env_name} is not configured" if self.env_name else "a Google API key is not configured")
            self.client = google.genai.Client(api_key=self.api_key)
        return self.client

    def request(self, model: str, contents: Any, config: Any = None, reasoning: Optional[str] = None) -> Any:
        """One ``generate_content``, counting the call and its tokens. With ``reasoning == "minimal"`` the thinking level is
        minimal (hidden reasoning cost ~11s per call on real prompts for the same output); a model that rejects the thinking
        config is retried once without it."""
        client = self.get_client()
        self.call_count += 1
        response = None
        if reasoning == "minimal":
            try:
                response = client.models.generate_content(model=model, contents=contents,
                                                          config={**(config or {}), "thinking_config": {"thinking_level": "minimal"}})
            except Exception as exc:  # noqa: BLE001
                if "think" not in str(exc).lower():
                    raise
        if response is None:
            response = client.models.generate_content(model=model, contents=contents, config=config or None)
        meta = getattr(response, "usage_metadata", None)
        if meta:
            self.tokens_in += getattr(meta, "prompt_token_count", 0) or 0
            self.tokens_out += getattr(meta, "candidates_token_count", 0) or 0
        return response

    @retry_transient(max_retries=3, base_delay=1.0)
    def resolve_model(self, model: str) -> str:
        """A bare family name ("gemini-flash") becomes the newest live id of that family; a concrete id passes through."""
        return resolve_model_name(model, self.list_models()) if is_family_name(model) else model

    def plan(self, prompt: str, *, model: str, tool_schema: Dict[str, Any],
             layers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Forced JSON output (Gemini has no tool_choice); a malformed response is re-asked, and after the retries the decision is {}. A missing key or library raises."""
        self.get_client()      # first: a missing key or library raises here, so a router can fail over; only a bad reply becomes {}
        model = self.resolve_model(model)
        instruction, contents = split_layers_for_gemini(None, layers) if layers else (None, prompt)
        config: Dict[str, Any] = {"response_mime_type": "application/json"}
        if instruction:
            config["system_instruction"] = instruction
        try:
            return parse_json_with_retry(lambda: self.request(model, contents, config).text,
                                         validate=lambda o: isinstance(o, (dict, list)), label="gemini planner")
        except Exception:  # noqa: BLE001
            return {}

    @retry_transient(max_retries=3, base_delay=1.0)
    def answer(self, messages: List[Dict[str, Any]], *, model: str, system: Optional[str] = None,
               layers: Optional[List[Dict[str, Any]]] = None, reasoning: Optional[str] = None) -> str:
        """With ``layers`` the head is a native system_instruction; otherwise the message list is flattened to one prompt, and an
        image block is sent as a real inline part (dropping the bytes would silently lose the user's picture)."""
        model = self.resolve_model(model)
        if layers:
            instruction, contents = split_layers_for_gemini(system, layers)
            response = self.request(model, contents, {"system_instruction": instruction} if instruction else None, reasoning)
            return response.text if response and response.text else ""
        parts = [f"System: {system}\n"] if system else []
        images: List[Dict[str, Any]] = []
        for msg in messages:
            role, content = msg.get("role", "user"), msg.get("content", "")
            for block in ([{"type": "text", "text": content}] if isinstance(content, str) else content if isinstance(content, list) else []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    parts.append(f"{role.capitalize()}: {block.get('text', '')}\n")
                elif block.get("type") == "image":
                    part = image_part(block)
                    images.append(part) if part is not None else parts.append("[Image included]\n")
        prompt = "".join(parts).strip()
        response = self.request(model, [{"role": "user", "parts": [{"text": prompt}, *images]}] if images else prompt, None, reasoning)
        return response.text if response and response.text else ""

    def supports_web_search(self, model: Optional[str] = None) -> bool:
        return bool(self.api_key)

    @retry_transient(max_retries=3, base_delay=1.0)
    def web_search(self, query: str, *, model: str, max_results: int = 5, instruction: Optional[str] = None) -> Dict[str, Any]:
        """Search through Google Search grounding (no extra key):
        ``{"answer", "results": [{title, url, snippet, passages, passage_kind, date}]}``. ``passages`` are the grounding supports
        tied to the page (sentences the model wrote, ``passage_kind`` "attributed"); ``snippet`` is the first. The API gives no
        page date, so ``date`` is empty. ``instruction`` is put before the query."""
        from google.genai import types
        config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        ask = f"{instruction.strip()}\n\n{query}" if instruction and instruction.strip() else query
        response = self.request(self.resolve_model(model), ask, config)
        results: List[Dict[str, Any]] = []
        for cand in (getattr(response, "candidates", None) or []):
            meta = getattr(cand, "grounding_metadata", None)
            supports = list(getattr(meta, "grounding_supports", None) or [])
            for index, chunk in enumerate(getattr(meta, "grounding_chunks", None) or []):
                web = getattr(chunk, "web", None)
                if web is None or len(results) >= max_results:
                    continue
                passages: List[str] = []
                for support in supports:
                    text = getattr(getattr(support, "segment", None), "text", "") or ""
                    if text and index in (getattr(support, "grounding_chunk_indices", None) or []) and text not in passages:
                        passages.append(text)
                results.append({"title": getattr(web, "title", "") or "", "url": getattr(web, "uri", "") or "",
                                "snippet": passages[0] if passages else "", "passages": passages,
                                "passage_kind": "attributed" if passages else "", "date": ""})
        return {"answer": getattr(response, "text", "") or "", "results": results}

    def supports_url_fetch(self, model=None) -> bool:
        return bool(self.api_key)

    @retry_transient(max_retries=2, base_delay=1.0)
    def fetch_url(self, url: str, *, model: str, instruction: Optional[str] = None) -> Dict[str, Any]:
        """Fetch ONE page through the url_context tool (Google retrieves it server-side, so it works where a plain GET is blocked):
        ``{"text", "url", "status"}``. Raises when the page could not be retrieved, so a caller can fall back to a direct GET."""
        from google.genai import types
        ask = instruction or ("Return the full visible text content of this page, verbatim and complete, as plain text with its "
                              "structure preserved. Do not summarize, comment, or add anything.")
        config = types.GenerateContentConfig(tools=[types.Tool(url_context=types.UrlContext())])
        response = self.request(self.resolve_model(model), f"{ask}\n\n{url}", config)
        status, retrieved = "", url
        for cand in (getattr(response, "candidates", None) or []):
            for entry in (getattr(getattr(cand, "url_context_metadata", None), "url_metadata", None) or []):
                status = str(getattr(entry, "url_retrieval_status", "") or "")
                retrieved = getattr(entry, "retrieved_url", "") or retrieved
                break
            if status:
                break
        text = getattr(response, "text", "") or ""
        if status and "SUCCESS" not in status.upper():
            raise RuntimeError(f"url_context could not retrieve {url}: {status}")
        if not text.strip():
            raise RuntimeError(f"url_context returned no content for {url}")
        return {"text": text, "url": retrieved, "status": status or "URL_RETRIEVAL_STATUS_SUCCESS"}

    @retry_transient(max_retries=2, base_delay=1.0)
    def fetch_models(self) -> List[str]:
        names = [m.name for m in self.get_client().models.list() if hasattr(m, "name") and "gemini" in m.name.lower()
                 and not any(skip in m.name.lower() for skip in ("robotics", "experimental", "exp-"))]
        if not names:
            log.warning("Gemini returned no usable models; using the fallback list")
        return names or list(FALLBACK_MODELS)

    def list_models(self) -> List[str]:
        return self.listing.get(self.fetch_models, FALLBACK_MODELS)
