"""MultiProvider: one provider object that routes each call to the provider serving its model id (by prefix, ``family``), steps
down a tier, or to a configured fallback model (``fallback_models``, any provider), when a model hits a quota or rate limit, has no
credit (a billing error), times out or its provider is down, and keeps the calling thread's token totals.

Everything specific to a consumer comes in through the constructor: the provider map, an optional tier registry for the step-down
(``top_models()``, ``resolve_tier(tier)``, ``lower_tier(tier)``), an optional usage tracker (``over_limit()``, ``record(tokens_in,
tokens_out, spec_id=, seconds=)``), the text shown when the tracker's limit is reached, and the id of the spec a call belongs to, and the ordered ``fallback_models``.
"""
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi import implementation

from ..ports.model import ModelProvider, answer_with_reasoning, plan_with_step
from ..ports.scope import ThreadLocalCounter
from . import outage
from .family import MODEL_PREFIX_PROVIDERS, provider_name_for_model

log = logging.getLogger("hubofhubs.models.router")
COOLDOWN_SECONDS = 600.0


def is_quota_or_rate_limit_error(exc: Exception) -> bool:
    """Whether ``exc`` reads as a quota or rate-limit failure; vendor SDKs share no exception type for it, so the text decides."""
    text = str(exc).lower()
    return any(marker in text for marker in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit"))


def is_failover_error(exc: Exception) -> bool:
    """Whether ``exc`` says this model cannot answer now but another may: a quota or rate limit, no credit or billing (the
    "credit balance is too low" of 2026-10-22), a timeout, or a provider outage. A bad request or a bug in the caller is not one:
    asking another provider would only hide it."""
    return is_quota_or_rate_limit_error(exc) or outage.is_billing_error(exc) or outage.is_outage(exc) or outage.is_timeout(exc)


@implementation("call-a-model", "multi_provider")
class MultiProvider(ModelProvider):
    # Per usage scope (ThreadLocalCounter): this instance is shared by tasks that run concurrently, and a turn resets and reads
    # these to report what it alone cost.
    call_count = ThreadLocalCounter()
    tokens_in = ThreadLocalCounter()
    tokens_out = ThreadLocalCounter()

    def __init__(self, primary: ModelProvider, providers: Optional[Dict[str, ModelProvider]] = None, usage_tracker: Any = None,
                 registry: Any = None, *, prefixes: Mapping[str, str] = MODEL_PREFIX_PROVIDERS,
                 limit_message: Callable[[], str] = lambda: "The usage limit is reached.",
                 spec_of: Callable[[], str] = lambda: "",
                 fallback_models: Sequence[str] = ()):
        super().__init__()
        self.fallback_models = tuple(fallback_models)   # ordered models to ask next (any provider) when no lower tier is left
        self.primary = primary
        self.providers = providers or {}
        self.usage_tracker = usage_tracker
        self.registry = registry
        self.prefixes = prefixes
        self.limit_message = limit_message
        self.spec_of = spec_of
        self.call_count = self.tokens_in = self.tokens_out = 0
        self.cooldown_until: Dict[str, float] = {}        # model -> monotonic time until which a quota-exhausted model is skipped
        self.cooldown_lock = threading.Lock()

    def tier_of(self, model: str) -> Optional[str]:
        """The tier that currently resolves to ``model``, or None (a pinned model, or no registry)."""
        try:
            return next((t for t, m in self.registry.top_models().items() if m == model), None) if self.registry and model else None
        except Exception:  # noqa: BLE001 - a registry hiccup must never break a call
            return None

    def lower_model(self, model: str, exc: Exception) -> Optional[str]:
        """The tier-registry model to retry with on a failover error, or None (not such an error, a pinned model, the cheapest
        tier, or a lower tier that resolves to the same model)."""
        tier = self.tier_of(model) if is_failover_error(exc) else None
        lower = self.registry.lower_tier(tier) if tier else None
        lower_model = self.registry.resolve_tier(lower) if lower else None
        return lower_model if lower_model and lower_model != model else None

    def next_model(self, model: str, exc: Exception, tried: Tuple[str, ...]) -> Optional[str]:
        """The model to ask after ``model`` failed with ``exc``: the next cheaper tier, else the first configured fallback model
        not yet tried, else None (the error is raised)."""
        lower = self.lower_model(model, exc)
        if lower is not None and lower not in tried:
            return lower
        if not is_failover_error(exc):
            return None
        return next((m for m in self.fallback_models if m not in tried), None)

    def call_with_fallback(self, model: str, make_call: Callable[[str], Any], tried: Tuple[str, ...] = ()) -> Any:
        """The one retry-and-step-down loop: ``make_call(m)`` performs one routed call for model ``m``; on a failover error (quota,
        rate limit, no credit, timeout, outage) the next cheaper tier is tried, then each configured fallback model, until a call
        succeeds or none is left (the last error is raised). A model that failed is skipped for ``COOLDOWN_SECONDS``: a per-model
        daily quota or an empty balance does not recover in seconds."""
        tried = tried + (model,)
        with self.cooldown_lock:
            cooling = self.cooldown_until.get(model, 0.0) > time.monotonic()
        skip_to = self.next_model(model, Exception("429 quota cooldown"), tried) if cooling else None
        if skip_to is not None:
            return self.call_with_fallback(skip_to, make_call, tried)
        try:
            return make_call(model)
        except Exception as exc:
            following = self.next_model(model, exc, tried)
            if following is None:
                raise
            with self.cooldown_lock:
                first = self.cooldown_until.get(model, 0.0) <= time.monotonic()
                self.cooldown_until[model] = time.monotonic() + COOLDOWN_SECONDS
            if first:
                log.warning("%s cannot answer now (%s); using %s for the next %d minutes", model, type(exc).__name__, following,
                            int(COOLDOWN_SECONDS // 60))
            return self.call_with_fallback(following, make_call, tried)

    def provider_for(self, model: Optional[str]) -> ModelProvider:
        """The provider serving ``model`` by prefix, else the primary."""
        name = provider_name_for_model(model or "", self.providers, self.prefixes)
        return self.providers[name] if name else self.primary

    def routed(self, model: str, call: Callable[[ModelProvider, str], Any]) -> Any:
        """One routed call with tier fallback; the token delta the provider reports is added to this object and the tracker."""
        def attempt(m: str) -> Any:
            provider = self.provider_for(m)
            before_in, before_out, started = getattr(provider, "tokens_in", 0), getattr(provider, "tokens_out", 0), time.monotonic()
            result = call(provider, m)
            delta_in = max(0, getattr(provider, "tokens_in", 0) - before_in)
            delta_out = max(0, getattr(provider, "tokens_out", 0) - before_out)
            if delta_in or delta_out:
                self.tokens_in += delta_in
                self.tokens_out += delta_out
                if self.usage_tracker is not None:
                    try:
                        self.usage_tracker.record(delta_in, delta_out, spec_id=self.spec_of(), seconds=time.monotonic() - started)
                    except Exception:  # noqa: BLE001 - token tracking must never break a call
                        pass
            return result
        return self.call_with_fallback(model, attempt)

    def over_limit(self) -> bool:
        return bool(self.usage_tracker and self.usage_tracker.over_limit())

    def plan(self, prompt: str, *, model: str, tool_schema: Dict[str, Any], layers: Optional[List[Dict[str, Any]]] = None,
             step: Optional[str] = None) -> Dict[str, Any]:
        """Route a plan call. Over the daily limit the decision is a terminal "answer", so no more model work is done."""
        if self.over_limit():
            return {"action": "answer", "rationale": "daily token limit reached"}
        self.call_count += 1
        return self.routed(model, lambda p, m: plan_with_step(p, prompt, model=m, tool_schema=tool_schema, layers=layers, step=step))

    def answer(self, messages: List[Dict[str, Any]], *, model: str, system: Optional[str] = None,
               layers: Optional[List[Dict[str, Any]]] = None, reasoning: Optional[str] = None, step: Optional[str] = None) -> str:
        """Route an answer call; ``reasoning`` and ``step`` reach only a provider whose ``answer`` declares them."""
        if self.over_limit():
            return self.limit_message()
        self.call_count += 1
        return self.routed(model, lambda p, m: answer_with_reasoning(p, messages, model=m, system=system, layers=layers,
                                                                      reasoning=reasoning, step=step))

    def supports_web_search(self, model: Optional[str] = None) -> bool:
        fn = getattr(self.provider_for(model) if model else self.primary, "supports_web_search", None)
        try:
            return bool(fn(model)) if callable(fn) else False
        except Exception:  # noqa: BLE001 - a capability probe must never raise
            return False

    def web_search(self, query: str, *, model: str, max_results: int = 5, instruction: Optional[str] = None) -> Dict[str, Any]:
        if self.over_limit():
            return {"answer": self.limit_message(), "results": []}
        self.call_count += 1
        return self.routed(model, lambda p, m: p.web_search(query, model=m, max_results=max_results,
                                                                    **({"instruction": instruction} if instruction else {})))

    def list_models(self) -> List[str]:
        """Every model from the primary and all registered providers, deduplicated."""
        found: List[str] = []
        for provider in [self.primary, *self.providers.values()]:
            try:
                found.extend(provider.list_models())
            except Exception:  # noqa: BLE001
                pass
        return list(set(found))
