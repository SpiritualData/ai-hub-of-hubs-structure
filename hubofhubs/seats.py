"""The seats: Protocol classes declared with ``@solution(id)`` in scope ``hubofhubs``. Importing this module runs nothing.

They are written ``typing.Protocol`` on purpose: esoi's port scan (S7) does not read intent-mode solutions, so the bare
``Protocol`` form is flagged as a port with no row. The seat is tied to its record by the solution id.

An implementation's constructor parameters typed with one of these Protocols are its needs (``esoi.assemble``).
``web-search`` is external too, but the hub executes
its default arms (SearXNG, JSON search APIs described as data, Gemini grounding, a provider's own search); none is selected by default.
"""
import typing
from typing import Any, Callable, List, Mapping, Optional, Sequence, Union, runtime_checkable

from esoi import solution

from .card import Card
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


@solution("vendor-model-caller", kind="event", entry="answer", example={"messages": [{"role": "user", "content": "Reply with the single word: ok"}], "model": "claude-haiku"})
@runtime_checkable
class ModelCalling(ModelProvider, typing.Protocol):
    """Plans, answers and lists models for one vendor (or, as the router, for several). External system: the hub ships arms over
    the vendor SDKs (extras ``anthropic``, ``gemini``, ``openai``) and a router; the consumer passes keys and settings as arguments."""


@solution("web-search", kind="event", entry="search", example="latest Rust release")
@runtime_checkable
class SearchBackend(typing.Protocol):
    """Runs one web search and returns a ``SearchResponse`` (hits with title, url, snippet, date, the separate ``passages`` and
    their ``passage_kind``; an optional direct answer; the queries issued); raises ``SearchBackendError`` on failure. An arm also
    carries a ``name`` attribute (the chain's label). ``instruction`` is the caller's own wording for a model-backed arm (for
    example "include facts that count against the claim"); an arm that is not model-backed accepts it and ignores it.
    External system: the hub ships arms, the consumer may provide its own."""

    def search(self, query: str, *, max_results: int = 5, instruction: Optional[str] = None) -> SearchResponse: ...


@solution("the-science", kind="event", entry="search", example="meditation and attention")
@runtime_checkable
class WorldKnowing(typing.Protocol):
    """Looks up what the world says now and returns it as ``Observation`` rows a reader can cite. ``search`` runs one or more queries
    and returns one compact observation (title, link and snippet per hit); ``fetch`` reads one page and returns the passages that bear
    on a focus, or the whole document one part at a time. Neither raises: a failure comes back as an observation of kind ``error``.
    An arm's search need is the ``web-search`` seat, which the consumer chooses."""

    def describe(self) -> str: ...
    def search(self, queries: Union[str, List[str]], *, max_results: Optional[int] = None, fresh: bool = False) -> Observation: ...
    def fetch(self, url: str, *, focus: Optional[str] = None, fresh: bool = False, full: bool = False,
              part: Optional[int] = None) -> Observation: ...


@solution("model-tier-chooser", kind="event", entry="choose", example={"available": ["anthropic"]})
@runtime_checkable
class TierSelection(typing.Protocol):
    """Per model tier, pick the (provider, model) arm with the most passing work per cost. ``choose`` reads the registry's own
    arms, prices and measurements and returns ``{tier: {arm, reason, scored}}``; ``select`` does the same for data you pass."""

    def choose(self, folder: Any = None, available: Optional[Sequence[str]] = None, credits: Optional[Sequence[Mapping[str, str]]] = None,
               **bars: Any) -> Mapping[str, Any]: ...

    def select(self, tiers: Mapping[str, Sequence[Mapping[str, Any]]], prices: Sequence[Mapping[str, str]],
               credits: Sequence[Mapping[str, str]] = (), defaults: Any = None, **bars: Any) -> Mapping[str, Any]: ...


@solution("research-freshness-reader", kind="event", entry="days_since", example="2026-10-01")
@runtime_checkable
class FreshnessReading(typing.Protocol):
    """Reads the registry's recorded dates and reports how old each area's research is."""

    def days_since(self, iso: str, clock: Any = None) -> Optional[int]: ...
    def combine(self, facts: Sequence[Mapping[str, Any]], connections: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...


class GoalRunning(typing.Protocol):
    """What the arms of the three goal-running tools share: take a goal with a written done-standard and try to bring it about, then return
    a ``DeepResult`` that says whether the goal was met. Never raises: a refusal or failure comes back as ``met=False`` with the reason, and
    nothing is changed when it declines. An arm also carries ``write_surface`` (what kind of change it can make: files, operations or an
    agent) and may stream ``ProgressEvent`` rows through ``emit``. The model it needs and the writer it is granted (``FileWriter``,
    ``OperationWriter``) are constructor arguments the consumer provides."""

    def run_goal(self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,
                 emit: Optional[Callable[[ProgressEvent], None]] = None, context_preamble: Optional[str] = None,
                 run_id: Optional[str] = None) -> DeepResult: ...


@solution("file-editing", kind="event", entry="run_goal", example={"goal": "add a line to NOTES.md", "brief": "one line, then stop"})
@runtime_checkable
class FileEditing(GoalRunning, typing.Protocol):
    """Changes a file by instruction and reports what changed (a ``DeepResult``). Every arm of this seat does that one job: a one-call
    model edit today, and exact string replacement or patch formats as researched candidates with no arm yet."""


@solution("connected-system-operations", kind="event", entry="run_goal", example={"goal": "add a line to NOTES.md", "brief": "one line, then stop"})
@runtime_checkable
class ConnectedOperating(GoalRunning, typing.Protocol):
    """Calls an operation of a connected system (a write through an MCP server today; a consumer declares its own system's operations as
    another arm) and reports the result as a ``DeepResult``."""


@solution("delegated-agent-sessions", kind="event", entry="run_goal", example={"goal": "add a line to NOTES.md", "brief": "one line, then stop"})
@runtime_checkable
class AgentSessions(GoalRunning, typing.Protocol):
    """Hands open-ended work to an agent that runs in its own session and reports back (a ``DeepResult``). The three arms are Claude Code
    agents, which are coding-oriented agents used as general ones; a general agent not tied to coding is a researched candidate with no arm yet."""


@solution("nervous-system", kind="event", entry="watch", example="delete the old backup folder")
@runtime_checkable
class RiskWatching(typing.Protocol):
    """Watches a run through a cheap digest and sends one signal: a ``RiskSignal`` (severity none, low, medium or high, and the reason). It does
    not route: what to do with a signal belongs to Judgment Calls (ask, proceed or decline for a person) and to the Planner and Delegation
    (answering now, handing work to an agent session, changing course). Never raises. The consumer's prompt is data passed to the arm, not part of
    the hub. ``watch`` reads a digest of one step with the arm's own model provider; ``oversee`` is the engine's older five-way verdict, with the
    provider and model you pass."""

    def digest(self, **fields: Any) -> str: ...
    def oversee(self, provider: Any, model: str, digest: str) -> Any: ...
    def watch(self, digest: str, model: str = "") -> Any: ...


@solution("cards-from-files", kind="event", entry="build", example={"root": ".", "files": [], "existing": {}})
@runtime_checkable
class CardsFromFiles(typing.Protocol):
    """Proposes cards for the files of a folder, in the card-store record shape; writes nothing."""

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]: ...
    def changed(self, root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]: ...


@solution("context-retriever", kind="event", entry="retrieve", example={"query": "where is the retry delay computed?", "files": {"net.py": "def retry_delay(attempt):\n    return 2 ** attempt\n", "ui.py": "def draw():\n    pass\n"}})
@runtime_checkable
class ContextRetrieval(typing.Protocol):
    """Picks, from a corpus of files, the pieces of text a task needs and returns them best first within a token budget (a list of hits: unit
    id, file, first line, score, tokens). An empty list means the arm judged that no context is needed. The corpus is passed as files (path to
    text), with an optional history of past changes (date, subject, files) that arms may learn from; an arm indexes a corpus once and keeps it."""

    def retrieve(self, query: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000, history: Sequence[Mapping[str, Any]] = ()) -> Sequence[Any]: ...


@solution("the-subconscious", kind="event", entry="recall", example="rust release")
@runtime_checkable
class Remembering(typing.Protocol):
    """Recalls what is known about a query: the area every memory arm competes in, whether it is built from the hub's parts
    (a card store searched directly) or is one product that stores, builds and recalls on its own."""

    def recall(self, query: str, limit: int = 5) -> Sequence[Card]: ...
    def prepare(self, request: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000) -> Mapping[str, Any]: ...


@solution("the-assembler", kind="event", entry="coverage", example={})
@runtime_checkable
class WholeAssembling(typing.Protocol):
    """Builds the whole from the best-measured arm of every seat and reports its coverage: which seats are built and, for each that is not, what
    exactly to pass or set. It runs nothing for a request; the flow of a request is The Self's."""

    def coverage(self, environ: Optional[Mapping[str, str]] = None) -> Mapping[str, Any]: ...


@solution("system-integrity", kind="event", entry="audit", example=["examplevendor"])
@runtime_checkable
class Genericity(typing.Protocol):
    """Audits the hub for consumer wording: the vendor-name branches in its own code for the terms you give, with how stale its
    research is and how much of it connects by configuration."""

    def audit(self, terms: Sequence[str]) -> Mapping[str, Any]: ...
    def audit_run(self, run: Mapping[str, Any]) -> Sequence[str]: ...


@solution("role-understanding", kind="event", entry="state_role", example="the-assembler")
@runtime_checkable
class RoleUnderstanding(typing.Protocol):
    """A seat defined and empty: states the role of a part (what it is responsible for, what it is not, who owns that) from its record, so a
    part and the Assembler can both read it."""

    def state_role(self, part_id: str) -> Mapping[str, Any]: ...


# ------------------------------------------------------------------ The Self

@solution("the-self", kind="event", entry="respond", example={"request": "what is the latest Rust release?", "person": ""})
@runtime_checkable
class SelfAnswering(typing.Protocol):
    """The Self responds to a request as the whole: Consciousness represents the person, Body says where the data lives, Intelligence processes the
    request with the person's authority, World's tools do the outside work, the run is recorded and Integrity audits it, and Consciousness learns
    from feedback. ``respond`` returns a ``Result`` whose ``steps`` say, for every part, whether it ran, was skipped or has no arm yet; no answer is
    made up when a part is missing. ``serve`` takes the waiting requests in through Consciousness and responds to each; ``act_unasked`` responds to
    what Proactivity says is due. ``cancelled`` stops the request, down to a running agent session. ``coverage`` and ``health`` report the assembly
    and whether the system stays generic."""

    def respond(self, request: str, person: str = "", feedback: Optional[Mapping[str, Any]] = None,
                cancelled: Optional[Callable[[], bool]] = None) -> Any: ...
    def serve(self, person: str = "") -> Sequence[Any]: ...
    def act_unasked(self, schedules: Sequence[Mapping[str, Any]], now: str = "", person: str = "") -> Sequence[Any]: ...
    def coverage(self) -> Mapping[str, Any]: ...
    def health(self) -> Mapping[str, Any]: ...


# ------------------------------------------------------------------ Body

@solution("the-body", kind="event", entry="describe", example="")
@runtime_checkable
class FormAndContext(typing.Protocol):
    """The AI system's form and internal context: ``describe`` reports where the system's data lives (each source says whether it belongs to the
    system or to a person), where its requests come from and which enduring integrations the AI may use, each declared by the system through an
    adapter; ``record_run`` keeps the run record the flow wrote. Body also owns the configuration, environment variables, secrets and stored
    authentication the tools need."""

    def describe(self, person: str = "") -> Mapping[str, Any]: ...
    def record_run(self, run: Mapping[str, Any]) -> str: ...


@solution("internal-context", kind="event", entry="read", example="rust release")
@runtime_checkable
class InternalContexting(typing.Protocol):
    """Reads a system's own context through the tool its declaration names (local files at a standard location by default) and returns it as
    cards; ``declared`` lists the sources the system declared, each with ``belongs_to`` (the system or a person) and the configuration, environment
    variables, secrets and stored authentication its tool needs; ``record`` keeps the run record the flow wrote, which Integrity audits."""

    def read(self, query: str, limit: int = 5) -> Sequence[Card]: ...
    def declared(self) -> Sequence[Mapping[str, Any]]: ...
    def record(self, run: Mapping[str, Any]) -> str: ...


@solution("the-hands", kind="event", entry="integrations", example="")
@runtime_checkable
class Connecting(typing.Protocol):
    """A seat defined and empty (Hands): lists a system's enduring integrations (its AI tool registry, LLM platform, guardrails) and says
    which are accessible to the AI and which are used."""

    def integrations(self, system: str = "") -> Sequence[Mapping[str, Any]]: ...


@solution("intake-sources", kind="event", entry="pull", example={"source": "", "limit": 10})
@runtime_checkable
class IntakeSourcing(typing.Protocol):
    """Body's intake adapters: ``sources`` lists where this system's requests come from (a chat, a task queue, a place meeting action items are
    written; a system declares its own), and ``pull`` takes the requests waiting at one of them (each a mapping with ``text``, ``person`` and
    ``source``), handing each over once."""

    def sources(self) -> Sequence[Mapping[str, Any]]: ...
    def pull(self, source: str = "", limit: int = 10) -> Sequence[Mapping[str, Any]]: ...


# ------------------------------------------------------------------ Intelligence

@solution("the-intelligence", kind="event", entry="process", example={"request": "what is the latest Rust release?", "person": ""})
@runtime_checkable
class InformationProcessing(typing.Protocol):
    """Processes one request: the long view is read, the request becomes a target with a budget, the Mind plans, delegates and writes, and the
    goal and the response quality are checked. When the goal is unmet the flow returns to the Planner within the budget; when the budget or the
    authority runs out it goes to Judgment Calls. Returns a mapping with ``answer``, ``attempts``, ``escalation`` (Judgment Calls' decision, when
    the flow stopped unmet) and ``steps``. ``proactive`` returns the triggers Proactivity says are due."""

    def process(self, request: str, person: str = "", representative: Optional[Mapping[str, Any]] = None,
                priorities: Optional[Mapping[str, Any]] = None, cancelled: Optional[Callable[[], bool]] = None) -> Mapping[str, Any]: ...
    def proactive(self, schedules: Sequence[Mapping[str, Any]], now: str = "") -> Sequence[Mapping[str, Any]]: ...


@solution("the-mind", kind="event", entry="think", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class Reasoning(typing.Protocol):
    """The Mind: takes in context, plans, delegates and writes for one request. ``authority`` is the Representative's, ``target`` the metric
    the request was translated into, ``guidance`` the Planner's nudge and ``profile`` the resolved quality profile and ``prepared`` what the Subconscious prepared. Returns a mapping with
    ``text``, ``results`` (one per delegated piece), ``pieces`` and ``steps``. On a replan, ``unmet`` is what the last attempt failed and ``outside``
    what its workers brought, which Context Intake takes in."""

    def think(self, request: str, authority: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
              guidance: Optional[Mapping[str, Any]] = None, profile: Optional[Any] = None, prepared: Optional[Mapping[str, Any]] = None,
              unmet: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None, budget: Optional[Any] = None,
              cancelled: Optional[Callable[[], bool]] = None) -> Mapping[str, Any]: ...


@solution("context-intake", kind="event", entry="take", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class ContextTaking(typing.Protocol):
    """The one intake of the Mind: takes what the Subconscious prepared and what the World brought and returns one view."""

    def take(self, request: str, prepared: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...


@solution("planner", kind="event", entry="plan", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class Planning(typing.Protocol):
    """Breaks a request into pieces (a list of mappings with ``piece``, ``sub_goal`` and ``tool``, the worker category that fits it or empty).
    On a replan, ``unmet`` carries the failed pieces and why, and a piece that already met its sub-goal is not planned again."""

    def plan(self, request: str, context: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
             guidance: Optional[Mapping[str, Any]] = None, unmet: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]: ...


@solution("delegation", kind="event", entry="delegate", example={"pieces": [], "authority": {}})
@runtime_checkable
class Delegating(typing.Protocol):
    """Hands each piece to the right worker, only when necessary, carrying the Representative's ``authority`` and the sub-goal's done-standard;
    returns one result per piece. It enforces three limits and owns the last: the authority (a worker category not allowed is refused), the
    goal record's ``budget`` (pieces and dollars) and cancellation (``cancelled`` is checked before each piece and reaches a running agent session
    through the worker's own stop hook). A piece it did not run comes back with ``refused`` and the reason."""

    def delegate(self, pieces: Sequence[Mapping[str, Any]], authority: Optional[Mapping[str, Any]] = None, budget: Optional[Mapping[str, Any]] = None,
                 cancelled: Optional[Callable[[], bool]] = None) -> Sequence[Mapping[str, Any]]: ...


@solution("response-writer", kind="event", entry="write", example={"results": [], "profile": None})
@runtime_checkable
class ResponseWriting(typing.Protocol):
    """Writes the plan, request or communication the Mind outputs for its reader, to the quality profile that applies."""

    def write(self, results: Sequence[Mapping[str, Any]], profile: Optional[Any] = None) -> str: ...


@solution("higher-mind", kind="event", entry="view", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class HigherMind(typing.Protocol):
    """The long view for one request: the objectives it serves, what is remembered and the guidance for the Planner, one step each."""

    def view(self, request: str, person: str = "") -> Mapping[str, Any]: ...


@solution("long-term-memory", kind="event", entry="recall", example={"query": "rust release", "person": ""})
@runtime_checkable
class LongTermMemory(typing.Protocol):
    """Retains what happened across requests under a retention policy and recalls it over the Body's store."""

    def recall(self, query: str, person: str = "", limit: int = 5) -> Sequence[Mapping[str, Any]]: ...
    def retain(self, item: Mapping[str, Any], person: str = "") -> str: ...


@solution("live-objectives", kind="event", entry="current", example="")
@runtime_checkable
class Objectives(typing.Protocol):
    """The live hierarchy of intents and goals across requests: ``current`` returns it, ``place`` puts a request under the objective it serves."""

    def current(self, person: str = "") -> Sequence[Mapping[str, Any]]: ...
    def place(self, request: str, person: str = "") -> Mapping[str, Any]: ...


@solution("guidance", kind="event", entry="nudge", example={"request": "what is the latest Rust release?", "objectives": []})
@runtime_checkable
class Guiding(typing.Protocol):
    """An infrequent longer-term nudge for the Planner, with the context-specific quality criteria; ``None`` when none is due."""

    def nudge(self, request: str, objectives: Sequence[Mapping[str, Any]] = ()) -> Optional[Mapping[str, Any]]: ...


@solution("the-intuition", kind="event", entry="offer", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class Intuiting(typing.Protocol):
    """What surfaces for a request unasked: the items closest to it, within a limit, for the Mind to take or ignore."""

    def offer(self, request: str, limit: int = 5) -> Sequence[Mapping[str, Any]]: ...


@solution("critical-thinking", kind="event", entry="evaluate", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class CriticalThinking(typing.Protocol):
    """Critical Thinking: ``translate`` turns a request into a target, ``evaluate`` checks the goal and judges the response against the
    quality profile resolved from the Representative, Guidance and Prioritization (the default profile when none is given)."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
    def evaluate(self, request: str, response: str = "", target: Optional[Mapping[str, Any]] = None, evidence: str = "",
                 representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                 priorities: Optional[Mapping[str, Any]] = None, outcome: Optional[Any] = None) -> Mapping[str, Any]: ...


@solution("esoi-application", kind="event", entry="apply", example={"change": {}})
@runtime_checkable
class EsoiApplying(typing.Protocol):
    """Creates and edits specs and metrics from a proposed change and runs the iterative improvement loop."""

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]: ...


@solution("metric-translation", kind="event", entry="translate", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class MetricTranslating(typing.Protocol):
    """Turns a request into a metric with a target value or improvement, adjustable in real time, applied to each sub-goal."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...


@solution("goal-completion", kind="event", entry="check", example={"goal": "answer the question", "done_standard": "a cited answer", "outcome": ""})
@runtime_checkable
class GoalCompleting(typing.Protocol):
    """Says whether a goal's condition was met against its done-standard: a mapping with ``met`` and ``reason``."""

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]: ...


@solution("response-quality", kind="event", entry="judge", example={"response": "See https://example.org/a for details.", "evidence": "https://example.org/a"})
@runtime_checkable
class ResponseJudging(typing.Protocol):
    """Judges a response against a quality profile (``QualityProfile``: named criteria with weights and targets; the default profile when none
    is given) and returns one finding per criterion the response does not meet, as strings. An empty list means the response held. The arm
    that exists today judges faithfulness to the evidence only (every link in the response must be in the evidence); ``critique`` is that
    judgment alone."""

    def judge(self, response: str, evidence: str = "", profile: Optional[Any] = None) -> Sequence[str]: ...
    def critique(self, answer: str, evidence: str = "") -> Sequence[str]: ...


@solution("proactivity", kind="event", entry="due", example={"schedules": [], "now": "2026-07-12T09:00:00Z"})
@runtime_checkable
class Proactive(typing.Protocol):
    """Lets the system act without being asked: given its standing schedules and the time, returns the triggers that are due (each a mapping
    with ``schedule``, ``reason`` and the ``request`` to run), by calendar period, by a requested run or by an event."""

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "") -> Sequence[Mapping[str, Any]]: ...


# ------------------------------------------------------------------ World

@solution("the-world", kind="event", entry="take_in", example="latest Rust release")
@runtime_checkable
class TakingIn(typing.Protocol):
    """Brings the outside world in for a query: a web search, and with ``scholarly=True`` the papers of the world-knowing seat too.
    Returns ``{"answer": text, "items": [hits with their sources]}``. ``stale_areas`` names the areas of the hub's research that are out of date
    (Learning's reading), which The Self reports in its health."""

    def take_in(self, query: str, scholarly: bool = False) -> Mapping[str, Any]: ...
    def stale_areas(self, today: str = "") -> Sequence[str]: ...


@solution("the-tools", kind="event", entry="use", example={"category": "web-search", "request": "latest Rust release"})
@runtime_checkable
class Tooling(typing.Protocol):
    """Uses the tool of one category (``web-search``, ``read-files``, ``file-editing``, ``connected-system-operations`` or
    ``delegated-agent-sessions``) by calling that category's entry point with the request. A category the Representative's authority does not
    allow is refused by Delegation, and a request that names the ``owner`` of the data it reads (a person) outside the ``data_scope`` of the
    ``authority`` it is given is refused here: data scope is enforced by Tools and by Body's adapters, which declare whose each source is."""

    def use(self, category: str, request: Any, cancel_check: Optional[Callable[[], bool]] = None, authority: Optional[Mapping[str, Any]] = None) -> Any: ...


@solution("read-files", kind="event", entry="read", example={"root": ".", "paths": []})
@runtime_checkable
class FileReading(typing.Protocol):
    """Reads and lists the text files of a folder, never outside it: the world-facing half of working with files that Cards From Files builds on."""

    def list(self, root: str, suffixes: Sequence[str] = ()) -> Sequence[str]: ...
    def read(self, root: str, paths: Sequence[str] = ()) -> Mapping[str, str]: ...


@solution("model-plumbing", kind="event", entry="ask", example={"prompt": "Reply with the single word: ok", "tier": "cheap"})
@runtime_checkable
class ModelPlumbing(typing.Protocol):
    """Asks a model for the answer to a prompt at a tier, using the model the tier chooser measured best for that tier, through the vendor the
    hub assembled. Also enforces the goal record's budget on the calls it makes: ``budget`` is the record's mutable ``budget`` mapping, and a call spends one of its ``model_calls``."""

    def ask(self, prompt: str, tier: str = "", budget: Optional[Any] = None) -> str: ...


@solution("the-learning", kind="event", entry="stale_areas", example="2026-11-03")
@runtime_checkable
class Staying(typing.Protocol):
    """Names the areas of the registry whose research is older than the ninety day bar on a given date (ISO, default today)."""

    def stale_areas(self, today: str = "") -> Sequence[str]: ...


# ------------------------------------------------------------------ Consciousness

@solution("the-consciousness", kind="event", entry="represent", example="")
@runtime_checkable
class HumanAdapting(typing.Protocol):
    """Adapts the system to a person: ``represent`` returns the person's Representative (authority, preferences, quality profile and
    priorities), ``receive`` takes in the requests people made, ``learn`` applies the person's feedback to specs and metrics."""

    def represent(self, person: str = "") -> Mapping[str, Any]: ...
    def receive(self, person: str = "") -> Sequence[Mapping[str, Any]]: ...
    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...


@solution("request-intake", kind="event", entry="receive", example={"person": ""})
@runtime_checkable
class RequestIntaking(typing.Protocol):
    """Takes in the requests people make, from every source Body declares, each attached to the person who made it; nothing a person asked is
    lost or taken twice."""

    def receive(self, person: str = "", sources: Sequence[str] = ()) -> Sequence[Mapping[str, Any]]: ...


@solution("the-representatives", kind="event", entry="represent", example="")
@runtime_checkable
class Representing(typing.Protocol):
    """The AI persona that acts for a person: returns the person's authority, preferences and quality profile."""

    def represent(self, person: str = "") -> Mapping[str, Any]: ...


@solution("judgment-calls", kind="event", entry="decide", example={"signal": {"signal": "proceed"}, "person": ""})
@runtime_checkable
class JudgmentCalling(typing.Protocol):
    """Decides for one person whether to ask, proceed or decline on a risk signal (severity and reason) or on a flow that stopped (``context``
    carries ``stopped``: budget or authority); the decision may be to a human, another agent or a delegate. It also owns ask timing: whether the
    ask blocks or waits, whether it is batched, and what may continue meanwhile. It decides, too, whether a change to specs or learning needs an ask."""

    def decide(self, signal: Mapping[str, Any], person: str = "", context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...


@solution("feedback-learning", kind="event", entry="learn", example={"person": "", "feedback": {}})
@runtime_checkable
class FeedbackLearning(typing.Protocol):
    """Turns a person's feedback into proposed edits to specs and metrics (never to prompts), including quality profile changes, for ESOI
    Application to apply."""

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...


@solution("prioritization", kind="event", entry="prioritize", example={"person": "", "request": "what is the latest Rust release?"})
@runtime_checkable
class Prioritizing(typing.Protocol):
    """Translates the priorities a person states or implies into ESOI milestones and weights, including quality profile weights."""

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
