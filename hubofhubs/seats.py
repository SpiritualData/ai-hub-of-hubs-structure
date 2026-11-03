"""The seats: Protocol classes declared with ``@solution(id)`` in scope ``hubofhubs``. Importing this module runs nothing.

They are written ``typing.Protocol`` on purpose: esoi's port scan (S7) does not read intent-mode solutions, so the bare
``Protocol`` form is flagged as a port with no row. The seat is tied to its record by the solution id.

An implementation's constructor parameters typed with one of these Protocols are its needs (``esoi.assemble``).
``model-call`` is an external seat with no hub arm: the consumer provides it. ``search-backend`` is external too, but the hub executes
its default arms (SearXNG, JSON search APIs described as data, Gemini grounding, a provider's own search); none is selected by default.
"""
import typing
from typing import Any, Callable, List, Mapping, Optional, Sequence, Union, runtime_checkable

from esoi import solution

from .card import Card
from .ports.context import ContextAssembler
from .ports.deep import DeepResult, ProgressEvent
from .ports.model import ModelProvider
from .ports.retrieval import Observation
from .ports.search import SearchResponse


@solution("card-store", kind="store", entry="search", example="rust release")
@runtime_checkable
class CardStore(typing.Protocol):
    """Keeps cards and finds them again."""

    def add(self, card: Card) -> str: ...
    def get(self, card_id: str) -> Optional[Card]: ...
    def search(self, query: str = "", limit: int = 10, tag: str = "") -> Sequence[Card]: ...
    def delete(self, card_id: str) -> bool: ...
    def count(self) -> int: ...


@solution("context-assembler", kind="event", entry="assemble", example="where does the card store tidy itself?")
@runtime_checkable
class ContextAssembling(ContextAssembler, typing.Protocol):
    """Selects and renders the context a task needs into one view (and the ids of the cards it drew on); never raises. The hub ships
    the composite arm, which runs several assemblers in order as one; a consumer's own retrieval arms are provided by the consumer."""


@solution("model-call", kind="event", entry="complete", example={"prompt": "Reply with the single word: ok", "tier": "fast"})
@runtime_checkable
class ModelCall(typing.Protocol):
    """Asks a model one question at a given tier and returns the text. External: the consumer provides it."""

    def complete(self, prompt: str, tier: str = "") -> str: ...


@solution("call-a-model", kind="event", entry="answer", example={"messages": [{"role": "user", "content": "Reply with the single word: ok"}], "model": "claude-haiku"})
@runtime_checkable
class ModelCalling(ModelProvider, typing.Protocol):
    """Plans, answers and lists models for one vendor (or, as the router, for several). External system: the hub ships arms over
    the vendor SDKs (extras ``anthropic``, ``gemini``, ``openai``) and a router; the consumer passes keys and settings as arguments."""


@solution("search-backend", kind="event", entry="search", example="latest Rust release")
@runtime_checkable
class SearchBackend(typing.Protocol):
    """Runs one web search and returns a ``SearchResponse`` (hits with title, url, snippet, date, the separate ``passages`` and
    their ``passage_kind``; an optional direct answer; the queries issued); raises ``SearchBackendError`` on failure. An arm also
    carries a ``name`` attribute (the chain's label). ``instruction`` is the caller's own wording for a model-backed arm (for
    example "include facts that count against the claim"); an arm that is not model-backed accepts it and ignores it.
    External system: the hub ships arms, the consumer may provide its own."""

    def search(self, query: str, *, max_results: int = 5, instruction: Optional[str] = None) -> SearchResponse: ...


@solution("know-the-world", kind="event", entry="search", example="meditation and attention")
@runtime_checkable
class WorldKnowing(typing.Protocol):
    """Looks up what the world says now and returns it as ``Observation`` rows a reader can cite. ``search`` runs one or more queries
    and returns one compact observation (title, link and snippet per hit); ``fetch`` reads one page and returns the passages that bear
    on a focus, or the whole document one part at a time. Neither raises: a failure comes back as an observation of kind ``error``.
    An arm's search need is the ``search-backend`` seat, which the consumer chooses."""

    def describe(self) -> str: ...
    def search(self, queries: Union[str, List[str]], *, max_results: Optional[int] = None, fresh: bool = False) -> Observation: ...
    def fetch(self, url: str, *, focus: Optional[str] = None, fresh: bool = False, full: bool = False,
              part: Optional[int] = None) -> Observation: ...


@solution("choose-a-model-tier", kind="event", entry="choose", example={"available": ["anthropic"]})
@runtime_checkable
class TierSelection(typing.Protocol):
    """Per model tier, pick the (provider, model) arm with the most passing work per cost. ``choose`` reads the registry's own
    arms, prices and measurements and returns ``{tier: {arm, reason, scored}}``; ``select`` does the same for data you pass."""

    def choose(self, folder: Any = None, available: Optional[Sequence[str]] = None, credits: Optional[Sequence[Mapping[str, str]]] = None,
               **bars: Any) -> Mapping[str, Any]: ...

    def select(self, tiers: Mapping[str, Sequence[Mapping[str, Any]]], prices: Sequence[Mapping[str, str]],
               credits: Sequence[Mapping[str, str]] = (), defaults: Any = None, **bars: Any) -> Mapping[str, Any]: ...


@solution("read-registry-freshness", kind="event", entry="days_since", example="2026-10-01")
@runtime_checkable
class FreshnessReading(typing.Protocol):
    """Reads the registry's recorded dates and reports how old each area's research is."""

    def days_since(self, iso: str, clock: Any = None) -> Optional[int]: ...
    def combine(self, facts: Sequence[Mapping[str, Any]], connections: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...


@solution("score-hub-connections", kind="event", entry="metrics", example={"facts": {}, "connections": []})
@runtime_checkable
class HubScoring(typing.Protocol):
    """Scores, per area, whether a hub is registered and connected by configuration, given a consumer's binding."""

    def evaluate(self, binding: Any, folder: Any = None, today: Any = None) -> Any: ...
    def check(self, fact: Mapping[str, Any], kind: str) -> Mapping[str, Any]: ...
    def metrics(self, facts: Mapping[str, Any], connections: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...


@solution("act-in-the-world", kind="event", entry="run_goal", example={"goal": "add a line to NOTES.md", "brief": "one line, then stop"})
@runtime_checkable
class Acting(typing.Protocol):
    """Takes a goal with a written done-standard and tries to bring it about outside the model (edit files, call a write operation,
    run an agent), then returns a ``DeepResult`` that says whether the goal was met. Never raises: a refusal or failure comes back as
    ``met=False`` with the reason, and nothing is changed when it declines. An arm also carries ``write_surface`` (what kind of change
    it can make: files, operations or an agent) and may stream ``ProgressEvent`` rows through ``emit``. The model it needs and the
    writer it is granted (``FileWriter``, ``OperationWriter``) are constructor arguments the consumer provides."""

    def run_goal(self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,
                 emit: Optional[Callable[[ProgressEvent], None]] = None, context_preamble: Optional[str] = None,
                 run_id: Optional[str] = None) -> DeepResult: ...


@solution("watch-for-risk", kind="event", entry="watch", example="delete the old backup folder")
@runtime_checkable
class RiskWatching(typing.Protocol):
    """Watches a run through a cheap digest and sends at most one small signal (proceed, redirect, answer_now, escalate_deep,
    escalate_human). Never raises. The consumer's prompt is data passed to the arm, not part of the hub. ``watch`` reads a digest
    of one step with the arm's own model provider; ``oversee`` is the same with the provider and model you pass."""

    def digest(self, **fields: Any) -> str: ...
    def oversee(self, provider: Any, model: str, digest: str) -> Any: ...
    def watch(self, digest: str, model: str = "") -> Any: ...


@solution("cards-from-files", kind="event", entry="build", example={"root": ".", "files": [], "existing": {}})
@runtime_checkable
class CardsFromFiles(typing.Protocol):
    """Proposes cards for the files of a folder, in the card-store record shape; writes nothing."""

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]: ...
    def changed(self, root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]: ...


@solution("remember-and-recall", kind="event", entry="recall", example="rust release")
@runtime_checkable
class Remembering(typing.Protocol):
    """Recalls what is known about a query: the area every memory arm competes in, whether it is built from the hub's parts
    (a card store searched directly) or is one product that stores, builds and recalls on its own."""

    def recall(self, query: str, limit: int = 5) -> Sequence[Card]: ...


@solution("assemble-the-whole", kind="event", entry="answer", example="what is the latest Rust release?")
@runtime_checkable
class WholeAnswering(typing.Protocol):
    """Answers free text with the best-measured arm of every seat it composes and returns a ``Result`` (answer, items with their
    sources, trace, the arms used). It also acts on a goal behind the risk watch (``act``) and reports whether the hub itself stays
    generic and current (``health``); ``model_only`` is the model's own words with a note that no source was consulted."""

    def answer(self, text: str) -> Any: ...
    def model_only(self, prompt: str, tier: str = "") -> Any: ...
    def act(self, goal: str, brief: str = "") -> Any: ...
    def health(self) -> Mapping[str, Any]: ...


@solution("take-in-the-world", kind="event", entry="take_in", example="latest Rust release")
@runtime_checkable
class TakingIn(typing.Protocol):
    """Brings the outside world in for a query: a web search, and with ``scholarly=True`` the papers of the world-knowing seat too.
    Returns ``{"answer": text, "items": [hits with their sources]}``."""

    def take_in(self, query: str, scholarly: bool = False) -> Mapping[str, Any]: ...


@solution("reason-and-answer", kind="event", entry="reason", example={"prompt": "Reply with the single word: ok", "tier": "cheap"})
@runtime_checkable
class Reasoning(typing.Protocol):
    """Asks a model for the answer to a prompt at a tier, using the model the tier chooser measured best for that tier."""

    def reason(self, prompt: str, tier: str = "") -> str: ...


@solution("think-critically", kind="event", entry="critique", example={"answer": "See https://example.org/a for details.", "evidence": "https://example.org/a"})
@runtime_checkable
class Critiquing(typing.Protocol):
    """Holds an answer to the evidence behind it: returns one finding per claim the evidence does not support (today, every link in
    the answer that the evidence does not contain). An empty list means the answer held."""

    def critique(self, answer: str, evidence: str = "") -> Sequence[str]: ...


@solution("stay-current", kind="event", entry="stale_areas", example="2026-11-03")
@runtime_checkable
class Staying(typing.Protocol):
    """Names the areas of the registry whose research is older than the ninety day bar on a given date (ISO, default today)."""

    def stale_areas(self, today: str = "") -> Sequence[str]: ...


@solution("connect-any-integration", kind="event", entry="config_share", example="web_search")
@runtime_checkable
class Connecting(typing.Protocol):
    """Reports the share of an area's hub connections that need no code, only configuration (all areas when none is named)."""

    def config_share(self, area: str = "") -> float: ...


@solution("keep-it-generic", kind="event", entry="audit", example=["examplevendor"])
@runtime_checkable
class Genericity(typing.Protocol):
    """Audits the hub for consumer wording: the vendor-name branches in its own code for the terms you give, with how stale its
    research is and how much of it connects by configuration."""

    def audit(self, terms: Sequence[str]) -> Mapping[str, Any]: ...
