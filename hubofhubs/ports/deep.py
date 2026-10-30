"""The deep-work ports: what a goal-driven run returns (``DeepResult``), what it reports along the way (``ProgressEvent``), the
``DeepRunner`` and writer Protocols (``FileWriter``, ``OperationWriter``) and ``ProgressSink``, with the nominal bases the arms
extend. Moved out of a consumer's core; nothing here knows a consumer, a database or an organization.

The Protocols are written ``typing.Protocol`` like the seats in ``hubofhubs.seats``: esoi's port scan (S7) does not read
intent-mode solutions.
"""
from __future__ import annotations

import abc
import typing
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, runtime_checkable

from .events import Mode


@dataclass
class ProgressEvent:
    """One thing that happened during a run, emitted by the orchestrator to a ProgressSink.

    The orchestrator emits these as it works; it does NOT decide what is shown, the sink
    (chosen by Mode) does. ``type`` is one of the ``EVENT_*`` constants above.
    """
    type: str
    text: Optional[str] = None             # human-facing message (status tick, reply, milestone)
    step: Optional[int] = None             # loop step index, when relevant
    action: Optional[str] = None           # the planner action, for plan/replan events
    decision_id: Optional[str] = None      # for decision events
    result_kind: Optional[str] = None      # for result/done events: "answer" | "deep" | "confirm"
    data: Dict[str, Any] = field(default_factory=dict)  # any extra structured payload

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type}
        for k in ("text", "step", "action", "decision_id", "result_kind"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.data:
            d["data"] = self.data
        return d


# ``DeepResult.launch_problem`` values.
LAUNCH_MISSING_PROGRAM = "missing_program"
LAUNCH_PERMISSION_DENIED = "permission_denied"


@dataclass
class DeepResult:
    """The outcome of a goal-driven deep run."""
    met: bool                 # True = the run met the written goal cleanly
    output: str = ""
    error: Optional[str] = None
    decision_id: Optional[str] = None   # set if the run needed a human decision instead
    # ASYNC HAND-OFF marker. True = this runner did NOT execute the goal inline; it queued the real
    # run to finish out-of-band and report its outcome back later (e.g. a chat deep runner that
    # creates a tracked task and returns a "task #N launched" sentinel). When set, the goal loop
    # trusts ``met`` and STOPS, it must not re-verify the sentinel ``output`` against the goal
    # (that always fails) nor relaunch, which would spawn a fresh task every iteration. The real
    # result is verified when it reflects back, not here. Inline runners leave this False.
    deferred: bool = False
    # Resource usage the worker reported for THIS run, when available (0 / 0.0 if the runner does
    # not report it). The goal loop accumulates these to enforce an overall token budget instead of
    # a fixed attempt count.
    tokens: int = 0           # input + output tokens consumed by the worker for this run
    cost_usd: float = 0.0     # worker-reported cost for this run, when available
    # OUT-OF-BAND future context (bullets the async card updater learns from). This is the channel
    # that keeps future context away from the PRIMARY PAYLOAD: a runner whose output is strictly
    # formatted (generated code, JSON, a patch) declares
    # ``future_context_channel = FUTURE_CONTEXT_VIA_FIELD`` and returns its bullets HERE, so nothing
    # is ever appended to ``output``. A prose runner may leave this empty and end its ``output``
    # with the delimited section instead; the orchestrator parses that section into this field and
    # strips it from ``output`` at the single seam where a runner returns, so by the time any
    # consumer sees ``output`` it is the clean payload and this field is the only carrier. Either
    # way the card updater reads exactly one place: ``future_context``.
    future_context: str = ""
    # HOW this run ended, when the runner can tell. ``limit_hit`` means the worker ran out of its
    # TURN BUDGET mid-flight (Claude Code's ``error_max_turns``) rather than failing: its work up to
    # that point is real and its session still holds everything it learned. The goal loop reads this
    # to CONTINUE the same session with a bigger budget instead of re-running the goal from a cold
    # start, which is what made a long task burn its whole budget again on rediscovery and still
    # report a bare failure. A runner that cannot tell leaves it False, and behaves exactly as before.
    limit_hit: bool = False
    # The worker session this run used, when the runner has one (Claude Code's ``--session-id``).
    # It is what a continuation resumes, so the follow-up attempt picks up the run's own context.
    session_id: Optional[str] = None
    # The runner is OUT OF MOVES for this goal: it already tried what it can this turn (its own
    # attempt budget is spent, or a retry reproduced a result it had already returned), so running
    # it again would only repeat the same work. The goal loop stops on this instead of re-launching
    # the runner with an augmented brief; the runner's ``output`` should already say, in plain words,
    # what it tried. Structural, set by the runner from its own bookkeeping, never inferred from the
    # text of its output. A runner that cannot tell leaves it False, and behaves exactly as before.
    exhausted: bool = False
    # Claude Code refused this run because the subscription USAGE LIMIT is reached (see
    # ``core.usage_limit``). Not a failed goal: nothing ran, or the run stopped mid-flight, and the
    # work belongs back in the queue until the limit resets. The goal loop stops on it at once (every
    # rung is a Claude model, so another rung would be refused too) and the task executor requeues
    # the task instead of reporting it. ``session_id`` still names the session to continue.
    usage_limited: bool = False
    # The run was STOPPED ON REQUEST (the caller's ``cancel_check`` reported a cancel while the
    # worker was running). The worker process was interrupted and, if it ignored that, terminated;
    # ``session_id`` still names the session so a later reply can resume the work already done.
    # Structural, set by the runner from its own stop, never inferred from any text. The goal loop
    # stops on it at once: no verifier call, no retry.
    cancelled: bool = False
    # The run was PAUSED on request (the caller's control channel asked for a pause). The process
    # was interrupted and released; ``session_id`` is what a resume continues. Not a failure and
    # not a cancel: the work belongs back on the thread until a person resumes it.
    paused: bool = False
    # Messages the run CLAIMED from its control channel and wrote to the worker, but whose arrival
    # at the model was never confirmed before the run ended (a stop, a pause or a crash). They are
    # returned here, as text, so nothing a person sent is silently lost: the caller shows them or
    # sends them with the resume. Empty for a run that saw everything it was given.
    unseen_inputs: List[str] = field(default_factory=list)
    # The worker NEVER STARTED the goal: the binary is missing or not executable, or the CLI refused
    # before its first model turn (an unrecognized model id, bad credentials, a rejected flag), so
    # it consumed nothing and did nothing. Its ``output`` (if any) is the CLI's own error text, not
    # work product. The goal loop treats this as a hard error: it never sends that text to the
    # verifier (which would dress the launch failure up as "goal not met") and never escalates the
    # model on it (a stronger model was never the problem). Structural, set by the runner from the
    # process outcome and its reported usage, never inferred from the wording of the output.
    launch_failed: bool = False
    # WHY the worker never started, when the runner knows it from the process outcome itself and never
    # from text: ``LAUNCH_MISSING_PROGRAM`` (the program is not installed, or not on the PATH) or
    # ``LAUNCH_PERMISSION_DENIED`` (it cannot be run). Empty for any other start failure (the CLI refused
    # before its first model turn: ``error`` carries its own words). A consumer that tells a person why
    # nothing ran words these two in its own plain language; only meaningful with ``launch_failed``.
    launch_problem: str = ""
    # The words in ``output`` were WRITTEN BY A MODEL answering in-process (a runner that declares
    # ``uses_deep_model = False``), not produced by a Claude Code worker that went and read things.
    # Set by the orchestrator from the runner it dispatched to, never by a runner. The link guard's
    # provenance rule reads it: such output is never evidence, and its links are judged like the
    # reply's own.
    model_written: bool = False
    # What a model-written run itself READ to produce ``output``, as plain text: the results of the
    # queries it executed, not anything it wrote. The only part of such a run that may vouch for an
    # address. A runner that cannot carry it leaves it empty.
    read_evidence: str = ""
    # The model this run actually executed with, when known. Set by the goal loop from the ladder
    # rung it dispatched to (``core/orchestrator.py``'s ``run_one``), not by the runner itself, so
    # every runner gets this for free; a runner that resolves its own model (or a future rung that
    # differs from what was requested) may overwrite it with the truer value.
    model: Optional[str] = None
    # The full model id the worker's CLI resolved ``model`` to (``sonnet`` -> ``claude-sonnet-...``),
    # read from the run's own session record. None when the runner cannot tell.
    resolved_model: Optional[str] = None
    # The orchestrator did NOT start this goal: the run was its OWN escalation (not something the
    # user or the planner asked for) and the runner the goal resolved to starts work that outlives
    # the turn (``DeepRunnerBase.starts_background_work``). Set by the orchestrator, never by a
    # runner; the escalation site then keeps the answer it already has.
    declined_background: bool = False
    # WHY a not-met run stopped, from the verifier's own verdict (one call, no extra LLM call):
    # ``verdict_reason`` / ``verdict_next_action`` are its last not-met reason and next step, so the
    # report can say what is left instead of only that the goal was not met. ``needs_person`` is the
    # specific question only a human can answer (the run stopped retrying because another attempt
    # could not help). ``unconfirmed_note`` is set on a run accepted as met whose only gap was proof
    # beyond what the request asked for: it names what was not independently confirmed.
    verdict_reason: str = ""
    verdict_next_action: str = ""
    needs_person: str = ""
    unconfirmed_note: str = ""
    # A tool, API or service the work needs failed in a way another attempt cannot change (the
    # verifier's ``tool_failure`` blocker), named in one plain sentence. The goal loop stops after
    # ``deep_tool_failure_attempts`` such verdicts instead of retrying and escalating the model.
    tool_failure: str = ""
    # The goal loop stopped because two attempts in a row fell short for the same reason, said the
    # same thing and changed nothing the runner can see (the verifier's reason, plain). Retrying,
    # or moving to a stronger model, would only repeat the attempt.
    stalled: str = ""
    # NOTHING CHANGED: the runner's own receipts of what it wrote show that this attempt changed
    # nothing in the system it acts on (no write completed, or every write matched nothing). It is
    # a structural fact the runner reports from its own bookkeeping, never inferred from the wording
    # of its output. Together with a not-met (or unverified) verdict it means the turn has no change
    # to report, so the goal loop must not let the result read as completed work; see
    # ``core/orchestrator.py``'s ``finish``. A runner that cannot tell leaves it False.
    changed_nothing: bool = False
    # THE OUTPUT ALREADY SAYS NOTHING CHANGED: the runner's own text carries a code-written sentence
    # stating that no change was made (set by the runner from its own bookkeeping, never inferred
    # from the wording). ``unconfirmed_no_change_text`` then adds no second lead line of its own, so
    # the person reads the no-change fact once. A runner that cannot tell leaves it False.
    states_no_change: bool = False
    # WHAT THIS RUN OBSERVED, one plain line each, built by the runner from its OWN records and
    # never from the wording of its output: a receipt for each change its write log proves landed,
    # and each source it really read back. This is the material the async card updater may draw a
    # new card fact from (see ``core/card_learning.py``); the run's reply text is not, because a
    # card is durable and a claim recorded as a fact grounds every later turn.
    observations: List[str] = field(default_factory=list)
    # THIS RUNNER RECORDS ITS OBSERVATIONS, so an EMPTY ``observations`` list means the run observed
    # nothing, rather than that the runner has no way to tell. Only with this set may the card
    # updater drop an edit for lack of support. A runner that cannot tell leaves it False and its
    # turns behave exactly as they did before.
    observations_reported: bool = False
    # AT LEAST ONE of ``observations`` above is a WRITE RECEIPT: a real change the runner's own
    # write log proves landed, not a read, a declined-write note, or an approval-parked marker.
    # Structural, set by the runner from its own write log, never inferred from the wording of its
    # output or of ``observations`` itself. This is what lets ``core/orchestrator.py``'s
    # ``result_landed_work`` tell a genuine PARTIAL write (the run is ``exhausted`` and not ``met``
    # because something else failed afterward, but part of the change already landed) apart from an
    # honest terminal ask that landed nothing (a clarifying question, a spent budget): both are
    # ``exhausted`` and not ``met``, and only the receipt flag tells them apart. A runner that
    # cannot tell leaves it False, which keeps today's "exhausted and not met -> not landed" rule
    # exactly as it was for every runner that does not set it.
    has_write_receipt: bool = False
    # HOW MANY CHANGES the runner's own records show LANDED in this attempt: an agent's file-changing tool uses that
    # completed without an error (the transcript of a Claude Code worker, an ACP tool call that reached ``completed``),
    # a file the fast editor wrote through its ``FileWriter``, an operation an ``OperationWriter`` accepted. Structural,
    # set by the runner from those records, never from its words. It is NOT ``has_write_receipt``: that flag means a
    # governed data write and feeds recipe learning, which a file edit must not. The metric flow reads both
    # (``core/goal_metrics.py``) to know the run changed something. 0 means none were seen, not that none happened:
    # a command a worker ran in a shell can change files and no record says so.
    changes_landed: int = 0
    # THE METRIC RECORD OF THIS GOAL, written by the goal loop from its metric ledger (``core/goal_metrics.py``), never by a
    # runner: one dict per metric, ``MetricResult.to_dict()`` (solution_id, metric_id, name, milestone, before, after, delta,
    # source, reason, disagrees; see docs/metric-results.md). Empty means nothing to show. ``metric_missing`` is set when
    # the run changed something (by the runner's own records) and no metric result was recorded for it, not even a
    # not-applicable, after the one request made for it.
    metric_results: List[Dict[str, Any]] = field(default_factory=list)
    metric_missing: bool = False


# The two ways a deep runner can hand its future-context bullets back. Declared per runner as
# ``DeepRunner.future_context_channel``; the orchestrator picks the matching brief instruction and
# reads the result from the matching place. Future context is asked for on BOTH channels: a
# code-generating runner has the most valuable future context of all (what it changed, which ids and
# schema it touched), so it is never opted out, only routed away from its payload.
FUTURE_CONTEXT_VIA_OUTPUT = "output"   # DEFAULT: worker ends its prose output with the delimiter


FUTURE_CONTEXT_VIA_FIELD = "field"     # strict-format runner: worker fills DeepResult.future_context


# What a deep runner's WRITE SURFACE is: what kind of change it is capable of making. Declared per
# runner as ``DeepRunner.write_surface`` (default ``WRITE_SURFACE_AGENT`` on ``DeepRunnerBase``, so
# an existing third-party runner behaves exactly as today). This is what lets the orchestrator tell
# a rung that can only edit files apart from one that changes data through a governed operation --
# a data change made through an operation must never be satisfied by a file-editing rung standing in for one.
WRITE_SURFACE_FILES = "files"            # the rung can only change files on disk


WRITE_SURFACE_OPERATIONS = "operations"  # the rung changes data through named, governed operations


WRITE_SURFACE_AGENT = "agent"            # a full agent: can do either, including writing code


@runtime_checkable
class DeepRunner(typing.Protocol):
    """Spawn a bounded, goal-driven autonomous run (the ``/goal --max-turns`` contract).

    OPTIONAL attribute ``future_context_channel`` (``FUTURE_CONTEXT_VIA_OUTPUT`` by default, or
    ``FUTURE_CONTEXT_VIA_FIELD`` for a runner whose output is a strict format such as generated code
    or JSON): it selects how this runner hands back the FUTURE-CONTEXT bullets the async card updater
    learns from. See ``DeepRunnerBase.future_context_channel`` for the full contract. It is read with
    ``getattr(..., default)``, so it is deliberately NOT a required Protocol member: a runner that
    never declares it keeps today's prose behaviour.

    OPTIONAL attribute ``write_surface`` (one of ``WRITE_SURFACE_FILES``, ``WRITE_SURFACE_OPERATIONS``,
    ``WRITE_SURFACE_AGENT``; ``WRITE_SURFACE_AGENT`` by default): declares WHAT KIND of change this
    rung is capable of making -- files on disk only, named governed operations only, or (the
    full-agent default) either, including writing code. The orchestrator reads it with
    ``getattr(..., WRITE_SURFACE_AGENT)`` to keep an operation-level data change off a rung that cannot satisfy
    it (the orchestrator of a consumer keeps such a ladder). A runner that never declares it
    is treated as a full agent, i.e. today's behaviour.
    """

    def run_goal(
        self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,
        emit: Optional[Callable[[ProgressEvent], None]] = None,
        context_preamble: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> DeepResult:
        """Run an autonomous worker toward ``goal`` (a written done-standard), bounded by
        ``max_turns``. Return a DeepResult distinguishing met-vs-limit. Never raises.

        ``emit`` (optional) lets a long-running deep runner report its EXECUTION LIFECYCLE as it
        works, generated code, each execution attempt, its raw output, retries, done, by emitting
        ``ProgressEvent(type=EVENT_EXEC, ...)``. The orchestrator routes these through the run's
        sink, so they show live (LIVE) and are dropped as chatter (BACKGROUND), exactly like other
        intermediate texture. Runners that don't stream may ignore it. The orchestrator only passes
        ``emit`` to runners whose ``run_goal`` accepts it, so older signatures keep working.

        ``context_preamble`` (optional) is a PER-CALL context preamble for THIS run only. The
        orchestrator forwards it (when the caller supplies one, e.g. an AI rep's pulled persona)
        so the run executes with that context without mutating any shared runner state. A runner
        that accepts it should prepend it ahead of its own configured preamble (or use it in
        place of one). Like ``emit``, it is passed ONLY to runners whose ``run_goal`` accepts it,
        so older signatures keep working and callers that pass nothing see prior behaviour.

        ``run_id`` (optional) is the STABLE id for this subgoal's whole retry sequence (the
        orchestrator generates it once per subgoal, before its first attempt). A runner that
        streams ``emit`` events should tag every event from every retry with this SAME id, since a
        retry may spawn an entirely new underlying process/session, without a stable id, a
        consumer's dashboard would otherwise show each retry as a separate duplicate run for what
        is really one ongoing subgoal. Passed ONLY to runners whose ``run_goal`` accepts it."""


@dataclass
class WriteResult:
    """The outcome of ONE attempted write through a ``FileWriter`` or an ``OperationWriter``.

    Deliberately a value, never an exception: a refused or failed write is an ordinary, expected
    outcome here (a path outside the root, a credential file, a read-only disk, an operation not
    on a write allowlist), and the caller's correct response is to report it and escalate, not to
    unwind. ``ok=False`` always means nothing changed: for a ``FileWriter`` the file on disk is
    UNCHANGED; for an ``OperationWriter`` the mutation was never attempted (a refusal) or the
    attempt failed (nothing on the far end changed).

    Shared by both write interfaces on purpose rather than each inventing its own result shape:
    ``rel_path`` doubles as "the path" for a file write and "the aliased operation name" for an
    ``OperationWriter`` call (e.g. ``"issues:create"``) -- both are just "the target, as the
    caller named it, for reporting". ``bytes_written``/``created``/``backup_path`` are FILE-write
    specific and left at their defaults (0/False/None) by an ``OperationWriter``, which instead
    fills ``detail`` with whatever adapter-specific payload it has (an MCP write's tool name and
    args, for auditability of what was -- or would have been -- executed).
    """
    ok: bool
    rel_path: str                          # the path (FileWriter) or aliased operation name
                                            # (OperationWriter) as the caller named it, for reporting
    error: Optional[str] = None            # why it was refused/failed; None on success
    bytes_written: int = 0
    created: bool = False                  # True = the file did not exist before this write
    backup_path: Optional[str] = None      # where the PREVIOUS content was saved, if anywhere
    detail: Optional[Dict[str, Any]] = None  # adapter-specific auditability payload (e.g. an


                                            # OperationWriter's {"tool": ..., "args": ...}); None
                                            # for a plain FileWriter result.


@runtime_checkable
class FileWriter(typing.Protocol):
    """WRITE side of the corpus boundary, the only way anything in this library changes a file.

    This is a separate interface from ``RetrievalAdapter`` on purpose. Retrieval is a read
    capability and every reference implementation of it is strictly read-only; writing is a
    different capability with a different blast radius, so it gets its own interface rather than
    being bolted onto the read one. A consumer that wires no ``FileWriter`` has, by construction,
    no code path in this library that can modify its files.

    IT IS OPT-IN. Nothing constructs one automatically: the consumer has to build a writer and
    hand it over (``RunnerConfig.file_writer``), which is the act of granting write access. The
    reference implementation is ``adapters.files_writer.FilesWriter``.

    An implementation MUST:
      * confine every path to its configured root, resolving symlinks and ``..`` BEFORE the
        containment test (``adapters.files_adapter.resolve_in_tree`` is the shared implementation);
      * refuse credential-ish files exactly as the read side does;
      * never raise, every refusal and every I/O failure comes back as ``WriteResult(ok=False)``.
    """

    def read_file(self, rel_path: str) -> Optional[str]:
        """Return the file's full text, or None if it is missing/unreadable/out of bounds.

        Present on the WRITER (rather than reusing a RetrievalAdapter read) because an edit has to
        be computed against the exact bytes the write will replace, resolved through the same
        boundary that will accept or refuse the write.
        """

    def write_file(self, rel_path: str, content: str) -> WriteResult:
        """Replace ``rel_path``'s entire content with ``content``. Never raises."""


@runtime_checkable
class OperationWriter(typing.Protocol):
    """WRITE side for a NAMED, SCHEMA-DESCRIBED mutating operation -- the general form of
    ``FileWriter`` for write capabilities broader than "replace a file's content" (send a
    message, create an issue, delete a row, ...). An MCP write tool is the motivating case, but
    nothing here is MCP-specific: any capability that mutates something outside a plain file is a
    NAMED operation with a schema, not a path+content pair, and belongs behind this interface
    instead of a special case inside the brain.

    Reuses ``WriteResult``'s value-not-exception contract rather than inventing a parallel result
    shape: ``ok=False`` always means nothing changed, ``error`` explains why, and ``detail``
    carries whatever adapter-specific auditability payload a caller needs (for an MCP operation,
    ``{"tool": ..., "args": ...}``) since a mutation here does not have a "path" the way a file
    write does.

    IT IS OPT-IN, same as ``FileWriter``: nothing constructs one automatically, and a consumer
    that wires none has, by construction, no code path in this library that can execute a
    mutating operation. The reference implementation is ``adapters.mcp_write_adapter.MCPWriteAdapter``.

    An implementation MUST:
      * refuse an operation not on its own write allowlist WITHOUT touching the network/backend at
        all (mirrors ``FileWriter``'s containment refusal, and mirrors ``RetrievalAdapter``'s own
        read-side allowlist refusal -- but a WRITE allowlist is its own, separate list: being
        allowlisted for READ grants nothing here);
      * never raise -- every refusal and every execution failure comes back as
        ``WriteResult(ok=False)``;
      * record which operation name and args were (or would have been) executed in
        ``WriteResult.detail``, for auditability, whether the call succeeded, failed, or was
        refused.
    """

    def list_writable_operations(self) -> List[Dict[str, Any]]:
        """``[{"name", "description", "input_schema"}, ...]`` for operations this instance may
        execute (i.e. exactly its own write allowlist, schema-described). Best-effort discovery
        for a caller building a prompt or a UI; an implementation that cannot introspect its own
        catalog returns ``[]``. Never raises.
        """

    def write_operation(self, name: str, args: Dict[str, Any]) -> WriteResult:
        """Execute ONE named mutating operation with ``args``. Never raises.

        Must refuse (``WriteResult(ok=False)``, no network/backend call) any ``name`` not on this
        instance's own write allowlist.
        """


@runtime_checkable
class ProgressSink(typing.Protocol):
    """The "inform along the way" discipline, the ONE place messaging policy lives.

    The orchestrator routes EVERY internal event through ``update(event, mode)``. The sink
    decides what (if anything) surfaces to the consumer. The orchestrator never decides
    messaging policy itself; it only emits. Mode is passed so a single sink could vary its
    behavior, but the two reference sinks below are mode-shaped by construction:

      * ``StreamSink``   , LIVE: forwards every event to the consumer's stream.
      * ``MilestoneSink``, BACKGROUND: drops planning/reading/re-planning chatter; forwards
                            only ``result`` / ``decision`` / ``milestone`` / ``done``.
    """

    def update(self, event: ProgressEvent, mode: Mode) -> None:
        """Receive one event. Decide whether/how it surfaces. Must never raise."""


class FileWriterBase(abc.ABC):
    """Nominal ABC parallel to the ``FileWriter`` Protocol (same pattern as the other adapters)."""

    @abc.abstractmethod
    def read_file(self, rel_path: str) -> Optional[str]: ...

    @abc.abstractmethod
    def write_file(self, rel_path: str, content: str) -> WriteResult: ...


class OperationWriterBase(abc.ABC):
    """Nominal ABC parallel to the ``OperationWriter`` Protocol (same pattern as the other
    adapters). ``list_writable_operations`` has a concrete default (``[]``, "nothing
    introspectable"), matching ``ModelProviderBase.supports_web_search``'s pattern of a
    non-abstract optional capability; an implementer that CAN describe its own catalog overrides
    it."""

    def list_writable_operations(self) -> List[Dict[str, Any]]:
        return []

    @abc.abstractmethod
    def write_operation(self, name: str, args: Dict[str, Any]) -> WriteResult: ...


class DeepRunnerBase(abc.ABC):
    # How THIS runner returns its future-context bullets (see FUTURE_CONTEXT_VIA_* above).
    #
    #   FUTURE_CONTEXT_VIA_OUTPUT (default) -- the runner's output is PROSE, so the worker is asked
    #       to end it with the delimited FUTURE-CONTEXT section. The orchestrator parses that section
    #       into ``DeepResult.future_context`` and strips it from ``DeepResult.output``.
    #
    #   FUTURE_CONTEXT_VIA_FIELD -- the runner's output is a STRICT FORMAT (generated code, JSON, a
    #       patch) where any appended prose would corrupt the payload. The worker is instead asked to
    #       return its bullets through the runner's own structured channel, and the runner puts them
    #       in ``DeepResult.future_context``. Nothing is ever appended to ``output``, so corruption
    #       is impossible by construction rather than by each consumer remembering to strip.
    #
    # Future context is asked for either way: a code generator knows the most reusable facts of all
    # (entities and ids touched, schema learned, files changed), and the card updater must keep
    # learning from exactly those turns. Read generically with ``getattr(runner,
    # "future_context_channel", FUTURE_CONTEXT_VIA_OUTPUT)``, so duck-typed runners keep working.
    future_context_channel: str = FUTURE_CONTEXT_VIA_OUTPUT

    # What kind of change THIS runner is capable of making (see WRITE_SURFACE_* above). Default is
    # the full agent, so an existing third-party runner that never sets this behaves exactly as
    # today -- only the two bounded rungs (FastEditRunner, MCPOperationRunner) narrow it.
    write_surface: str = WRITE_SURFACE_AGENT

    # Whether THIS runner actually runs the deep-model ladder's ``model`` (see
    # ``runner_uses_deep_model``). True by default, so every existing runner keeps today's
    # behaviour. A runner that answers in-process with its own fixed model (or queues the work for
    # another lane, which picks its own) sets False: the goal loop then never tells a person the
    # work "ran on sonnet" or is "retrying with opus", because neither would be true.
    uses_deep_model: bool = True

    # Whether THIS runner's work OUTLIVES the turn: it queues a task, schedules a job or otherwise
    # starts something that runs and leaves a trace after the reply (see ``runner_starts_background
    # _work``). False by default. The orchestrator never sends its OWN escalations (the verifier's
    # "need more context" and the last-resort deep run before giving up) to such a runner: those
    # runs are the assistant's initiative, and a durable job the person never asked for is a side
    # effect, not a better answer. A planner or user hand-off to the same runner is unaffected.
    starts_background_work: bool = False

    @abc.abstractmethod
    def run_goal(self, *, goal, brief, model=None, max_turns=None, emit=None,
                 context_preamble=None, run_id=None) -> DeepResult: ...


def runner_starts_background_work(runner: Any) -> bool:
    """Whether ``runner`` starts work that outlives the turn (``starts_background_work``). Read
    with ``getattr(..., False)`` so a duck-typed runner keeps today's behaviour."""
    return bool(getattr(runner, "starts_background_work", False)) if runner is not None else False


def runner_uses_deep_model(runner: Any) -> bool:
    """Whether ``runner`` executes with the deep-model ladder's ``model`` argument.

    Read with ``getattr(..., True)`` so a duck-typed runner that never declares
    ``uses_deep_model`` keeps today's behaviour. ``None`` (no runner wired) is False: nothing runs,
    so no model can be claimed for it."""
    if runner is None:
        return False
    return bool(getattr(runner, "uses_deep_model", True))


class ProgressSinkBase(abc.ABC):
    @abc.abstractmethod
    def update(self, event: ProgressEvent, mode: Mode) -> None: ...
