"""The model port: ``ModelProvider`` and the step hints and reasoning helpers that go with it.

Split out of ``adapters.py`` by definition; that module re-exports every name here.
"""
from __future__ import annotations

import abc
import typing
from typing import Any, Dict, List, Optional, runtime_checkable

from .scope import ThreadLocalCounter


def accepts_reasoning_hint(provider: Any) -> bool:
    """Whether ``provider.answer`` declares a ``reasoning`` keyword (or ``**kwargs``). Never raises."""
    import inspect
    try:
        params = inspect.signature(provider.answer).parameters.values()
    except (TypeError, ValueError, AttributeError):
        return False
    return any(p.name == "reasoning" or p.kind is p.VAR_KEYWORD for p in params)


# --- step hints: which ROLE this one LLM call plays in a turn --------------
#
# Mirrors ``reasoning`` above: an OPTIONAL keyword a provider MAY declare on ``plan``/``answer`` so
# the CONSUMER's own provider implementation can choose a model and/or sampling profile per call
# role (e.g. a stronger model on REPLY/VERIFY, low/deterministic temperature on JUDGE/SELECT).
# This library never bakes a model name or temperature to a step; it only plumbs the role name
# through. Keep this vocabulary SMALL -- do not add a constant without a real new role.
STEP_PLAN = "plan"              # the planner's own decision of what to do next this turn.


STEP_VERIFY = "verify"          # goal verification: did the work meet the goal.


STEP_REPLY = "reply"            # the user-facing reply/answer text.


STEP_NARRATION = "narration"    # the Narrator's optional first-beat line. Its own role so a failed or
                                # refused beat is never recorded under STEP_REPLY and can never fail the turn.


STEP_SELECT = "select"          # relevance filters, query generation, selection among candidates.


STEP_JUDGE = "judge"            # reach/intent/directive/target-for-turn/mode-release judges, overseer.


STEP_UNDERSTAND = "understand"  # understanding/interpreting input.


STEP_SUMMARIZE = "summarize"    # concise summaries, explanations, card/content updates.


def accepts_step_hint(fn: Any) -> bool:
    """Whether a provider callable (``provider.plan`` or ``provider.answer``) declares a ``step``
    keyword (or ``**kwargs``). Never raises.

    Takes the callable itself, not the provider, since the step hint applies to BOTH ``plan`` and
    ``answer`` (unlike ``accepts_reasoning_hint`` above, which only ever checks ``answer``).
    """
    import inspect
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError, AttributeError):
        return False
    return any(p.name == "step" or p.kind is p.VAR_KEYWORD for p in params)


def answer_with_reasoning(provider: Any, messages: List[Dict[str, Any]], *, model: Optional[str],
                          reasoning: Optional[str] = None, step: Optional[str] = None,
                          **kwargs: Any) -> str:
    """``provider.answer(...)``, passing the ``reasoning`` and/or ``step`` hints only when the
    provider takes them.

    The one place that decides whether either hint is forwarded, so a provider (or test fake, or
    wrapper) that predates one or both keeps working unchanged. See ``ModelProvider.answer``.
    """
    call_kwargs: Dict[str, Any] = dict(kwargs)
    if reasoning and accepts_reasoning_hint(provider):
        call_kwargs["reasoning"] = reasoning
    if step and accepts_step_hint(provider.answer):
        call_kwargs["step"] = step
    return provider.answer(messages, model=model, **call_kwargs)


def plan_with_step(provider: Any, prompt: str, *, step: Optional[str] = None,
                   **kwargs: Any) -> Dict[str, Any]:
    """``provider.plan(...)``, passing the ``step`` hint only when the provider takes it.

    Sibling of ``answer_with_reasoning`` for ``plan`` (which has no ``reasoning`` hint to carry):
    the same accepts-check, so a provider (or test fake, or wrapper) that predates ``step`` keeps
    working unchanged. See ``ModelProvider.plan``.
    """
    if step and accepts_step_hint(provider.plan):
        return provider.plan(prompt, step=step, **kwargs)
    return provider.plan(prompt, **kwargs)


@runtime_checkable
class TierResolving(typing.Protocol):
    """Turns a tier name (``fast``, ``balanced``, ``quality``, ``best`` or the consumer's own) into a model id."""

    def resolve_tier(self, tier: str) -> str: ...


@runtime_checkable
class ModelProvider(typing.Protocol):
    """The LLM behind planning, answering, and the live model list."""

    def plan(self, prompt: str, *, model: str, tool_schema: Dict[str, Any],
             layers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """One cheap, forced-structured planner call -> the raw decision dict.

        ``layers`` (optional) is the ordered prompt-layer blocks from ``core.prompt_layers``
        (``[{"text": str, "cache": bool}, ...]``, stable head + context first, volatile tail last).
        A provider that supports prefix caching renders the ``cache=True`` blocks as its cacheable
        prefix (e.g. an Anthropic ``system`` array with ``cache_control`` breakpoints, or a Gemini
        ``system_instruction`` + stable ``contents``) so a turn's repeated calls read the shared
        prefix instead of re-sending it. A provider that supports no caching (or is given no
        ``layers``) MUST behave exactly as before, using ``prompt``; callers always pass a faithful
        flattened ``prompt`` as well, so ignoring ``layers`` is a safe, no-behavior-change fallback.

        A provider MAY also accept an optional ``step`` keyword (one of the ``STEP_*`` constants
        above, e.g. ``STEP_PLAN``/``STEP_JUDGE``/``STEP_VERIFY``): never required, it names the ROLE
        this call plays so the provider can pick its own model/sampling for that role. It is never
        passed to a provider whose ``plan`` does not declare it; callers go through
        ``plan_with_step`` below, which checks.
        """

    def answer(self, messages: List[Dict[str, str]], *, model: str, system: Optional[str] = None,
               layers: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate a grounded reply from a message list. Returns the text.

        ``layers`` (optional) carries the ordered prompt-layer blocks (see ``plan``); a
        cache-aware provider renders the cacheable head + context prefix from them and takes the
        volatile tail as the final turn, while a provider given no ``layers`` uses ``messages``
        unchanged. Callers always build ``messages`` faithfully too, so ``layers`` is purely an
        additive cache hint.

        A provider MAY also accept an optional ``reasoning`` keyword (``"minimal"`` today): a
        hint that the call is a selection/classification step that gains nothing from hidden
        reasoning, so a model with a configurable thinking budget should spend as little as it
        allows. It is never passed to a provider whose ``answer`` does not declare it; callers go
        through ``answer_with_reasoning`` below, which checks.

        A provider MAY also accept an optional ``step`` keyword, the same ``STEP_*`` role hint
        ``plan`` above takes: never required, and never passed to a provider whose ``answer`` does
        not declare it (``answer_with_reasoning`` checks this too, alongside ``reasoning``).
        """

    def list_models(self) -> List[str]:
        """The live, latest-first model id list (model_registry buckets it into tiers)."""

    def supports_web_search(self, model: Optional[str] = None) -> bool:
        """Whether this provider can search the live web natively (no extra API key).

        Optional capability. Providers that wrap an SDK with a built-in web-search tool
        (Anthropic's ``web_search`` server tool, Gemini's Google Search grounding) return
        True when their LLM key is configured; others return False.
        """

    def web_search(self, query: str, *, model: str, max_results: int = 5, instruction: Optional[str] = None) -> Dict[str, Any]:
        """Search the live web via the provider's NATIVE tool and return a result dict.

        Returns ``{"answer": <synthesized text>, "results": [{"title","url","snippet"}, ...]}``; a row may also carry
        ``passages`` (list), ``passage_kind`` ("verbatim" or "attributed") and ``date``. ``instruction`` is the caller's own wording.
        Uses the same LLM API key the provider already has (no separate web-search key).
        Callers should gate on ``supports_web_search(model)`` first.
        """


class ModelProviderBase(abc.ABC):
    """Nominal base of the provider arms: per-usage-scope counters (``ThreadLocalCounter``), because one provider instance is shared
    by tasks running concurrently and each turn reads only its own ``tokens_in`` / ``tokens_out``."""
    call_count = ThreadLocalCounter()
    tokens_in = ThreadLocalCounter()
    tokens_out = ThreadLocalCounter()

    def __init__(self):
        self.call_count = 0
        self.tokens_in = 0
        self.tokens_out = 0

    @abc.abstractmethod
    def plan(self, prompt, *, model, tool_schema, layers=None) -> Dict[str, Any]: ...
    @abc.abstractmethod
    def answer(self, messages, *, model, system=None, layers=None) -> str: ...
    @abc.abstractmethod
    def list_models(self) -> List[str]: ...

    def supports_web_search(self, model: Optional[str] = None) -> bool:
        return False

    def web_search(self, query: str, *, model: str, max_results: int = 5, instruction: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("web search not supported by this provider")
