"""OpenAIProvider: plan (JSON mode), answer and the live model list over the OpenAI chat API, and DeepSeekProvider, the same
adapter pointed at DeepSeek's OpenAI-compatible endpoint. Needs the ``openai`` extra, imported on first use. Keys, base urls and
vendor request options are constructor arguments; nothing is read from the environment."""
from typing import Any, Dict, List, Optional, Sequence

from esoi import implementation

from ..ports.model import ModelProviderBase
from .family import is_family_name, resolve_model_name
from .listing import ModelListCache
from .retry import parse_json_with_retry, retry_transient

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@implementation("call-a-model", "openai")
class OpenAIProvider(ModelProviderBase):
    """``base_url`` points at any OpenAI-compatible endpoint (a proxy, vLLM, Ollama, a gateway); ``keyless`` allows a
    self-hosted one that takes no key. ``create_kwargs`` are extra keyword arguments for every completion; ``model_marker`` is the
    substring that keeps a listed model id; ``fallback_models`` is the list used when listing fails. ``keyless`` left unset means
    keyless exactly when a ``base_url`` is given."""
    ENVIRON = {"api_key": "OPENAI_API_KEY", "base_url": "OPENAI_BASE_URL"}      # option <- variable (esoi.assemble)
    ENVIRON_REQUIRED = (("api_key", "base_url"),)                                # a key, or an endpoint that takes none

    def __init__(self, *, api_key: Optional[str] = None, cache_seconds: float = 3600.0, base_url: Optional[str] = None,
                 keyless: Optional[bool] = None, create_kwargs: Optional[Dict[str, Any]] = None, model_marker: str = "gpt",
                 fallback_models: Sequence[str] = ("gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"),
                 env_name: Optional[str] = None):
        super().__init__()
        self.api_key = api_key
        self.env_name = env_name           # the consumer's name for where the key comes from, so a missing key can name it
        self.base_url = base_url
        self.keyless = bool(base_url) if keyless is None else keyless
        self.create_kwargs = dict(create_kwargs or {})
        self.model_marker = model_marker
        self.fallback_models = tuple(fallback_models)
        self.client = None
        self.listing = ModelListCache(cache_seconds)

    def get_client(self):
        if self.client is None:
            try:
                from openai import OpenAI  # lazy: the openai extra
            except ImportError:
                raise RuntimeError("openai is not installed. Install it with: pip install openai")
            if not self.api_key and not self.keyless:
                raise RuntimeError(f"{self.env_name} is not configured" if self.env_name else "an API key is not configured")
            kwargs: Dict[str, Any] = {"api_key": self.api_key or "not-needed"}     # the SDK needs a non-empty string
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)
        return self.client

    def complete(self, model: str, messages: List[Dict[str, Any]], **kwargs: Any) -> Any:
        """One chat completion, counting its tokens."""
        response = self.get_client().chat.completions.create(model=model, messages=messages, **kwargs, **self.create_kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.tokens_in += getattr(usage, "prompt_tokens", 0) or 0
            self.tokens_out += getattr(usage, "completion_tokens", 0) or 0
        return response

    @retry_transient(max_retries=3, base_delay=1.0)
    def resolve_model(self, model: str) -> str:
        """A bare family name ("gpt") becomes the newest live id of that family; a concrete id passes through."""
        return resolve_model_name(model, self.list_models()) if is_family_name(model) else model

    def plan(self, prompt: str, *, model: str, tool_schema: Dict[str, Any],
             layers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """JSON mode (``layers`` is accepted and ignored: no prompt-cache wiring here); a malformed response is re-asked, and
        after the retries the decision is {}. A missing key or library raises."""
        self.get_client()      # first: a missing key or library raises here, so a router can fail over; only a bad reply becomes {}
        model = self.resolve_model(model)
        ask = lambda: self.complete(model, [{"role": "user", "content": prompt}],
                                    response_format={"type": "json_object"}).choices[0].message.content or ""
        try:
            return parse_json_with_retry(ask, validate=lambda o: isinstance(o, (dict, list)), label="openai planner")
        except Exception:  # noqa: BLE001
            return {}

    @retry_transient(max_retries=3, base_delay=1.0)
    def answer(self, messages: List[Dict[str, Any]], *, model: str, system: Optional[str] = None,
               layers: Optional[List[Dict[str, Any]]] = None) -> str:
        """``layers`` is accepted and ignored; ``messages`` are used unchanged."""
        model = self.resolve_model(model)
        api_messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
        response = self.complete(model, api_messages)
        return response.choices[0].message.content if response and response.choices else ""

    @retry_transient(max_retries=2, base_delay=1.0)
    def fetch_models(self) -> List[str]:
        return [m.id for m in self.get_client().models.list().data if hasattr(m, "id") and self.model_marker in m.id.lower()]

    def list_models(self) -> List[str]:
        return self.listing.get(self.fetch_models, self.fallback_models)


@implementation("call-a-model", "deepseek")
class DeepSeekProvider(OpenAIProvider):
    """DeepSeek's OpenAI-compatible API. Thinking is off by default (slower, and more output tokens when on)."""
    ENVIRON = {"api_key": "DEEPSEEK_API_KEY", "base_url": "DEEPSEEK_BASE_URL"}
    ENVIRON_REQUIRED = ("api_key",)

    def __init__(self, *, api_key: Optional[str] = None, cache_seconds: float = 3600.0, base_url: Optional[str] = None,
                 thinking: bool = False, env_name: Optional[str] = None):
        super().__init__(api_key=api_key, cache_seconds=cache_seconds, base_url=base_url or DEEPSEEK_BASE_URL, keyless=False, env_name=env_name,
                         create_kwargs={} if thinking else {"extra_body": {"thinking": {"type": "disabled"}}},
                         model_marker="deepseek", fallback_models=("deepseek-flash", "deepseek-v4-pro"))
