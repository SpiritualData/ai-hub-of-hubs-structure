"""The hub's own harness as a ``DeepRunner``: it runs ``solution_loop.run_loop`` over a pure completion instead of delegating the goal to an
external coding agent.

Each model call is a pure text completion (the hub's Claude CLI provider, on the operator's subscription login, with no tools and no agent
prompt); this code executes the actions the reply holds. An arm is this harness with a tier, written
``solution_loop_runner@provider=anthropic,tier=fast``. The goal text is ``brief or goal``; its context is the caller's preamble plus the settings'
standing instructions, as the sibling runners send them.

Every deployment value comes from ``SubprocessConfig`` (working folder, wall-clock cap, extra PATH folders, the binary) and ``GoalSettings``
(the child environment, standing instructions). Nothing here reads ``os.environ``. ``as_solution_worker`` lets the solution hierarchy of
``solution_workers.work_solution`` use this runner as its worker.

Four capabilities sit on top of the loop. Every command runs in a bubblewrap sandbox (``sandbox=True``, whole disk read-only, the working folder
and a private temp folder writable) when bubblewrap is on the machine, and with only the refusal floor otherwise. Each run keeps a session file
(one JSON file per session id in ``session_dir``) after every call, and ``run_goal(resume_session_id=...)`` continues it. ``steer`` hands a
running session a message from the person. ``tools`` are operations beyond the shell that the consumer hands the loop.
"""
from __future__ import annotations

import os
import queue
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from esoi import implementation

from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_world.tools.deep import DeepResult, DeepRunnerBase, ProgressEvent
from hubofhubs.the_world.tools.command_running import sandbox_wrap
from hubofhubs.the_world.tools.delegated_agent_sessions import providers
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import extract_escalation_id
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig, log
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import (
    GoalSettings, GoalSettingsSource, resolve_goal_settings, with_instructions_pack)
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import LoopResult, LoopState, Tool, run_loop
from hubofhubs.the_world.tools.events import EVENT_EXEC

DEFAULT_TIER = "fast"
DEFAULT_CALLS = 15
DEFAULT_TIMEOUT_SECONDS = 1800.0   # a run with no configured cap still ends
SESSION_FOLDER = "solution-loop-sessions"


@implementation("delegated-agent-sessions", "solution_loop_runner")
class SolutionLoopRunner(DeepRunnerBase):
    """The hub's own tool loop: one pure completion per call, actions run by hub code, a folder map and the files in view rebuilt at each call."""

    REQUIRES = (needs.CLAUDE_BINARY, needs.CLAUDE_ACCOUNT, needs.CLAUDE_CLI_BOUNDARY, needs.WRITE_ROOT)
    PROVIDERS = ("anthropic",)   # the default completion is the Claude CLI provider; an injected ``complete`` can serve any model
    PAID = True                  # every run calls a model: never run by a free (offline) metric run
    config_class = SubprocessConfig
    on_trial = True              # measured and ranked beside the other harnesses, not chosen for a consumer until the owner promotes it

    def __init__(self, config: Optional[SubprocessConfig] = None, *, root: str = "", provider: str = "anthropic", tier: str = DEFAULT_TIER,
                 settings: Optional[GoalSettingsSource] = None, model_for: Optional[Callable[[str, str], Optional[str]]] = None,
                 instructions: str = "", complete: Optional[Callable[[str, str], str]] = None,
                 model_translator: Optional[Callable[[Optional[str]], Optional[str]]] = None, sandbox: bool = True, review: Any = True,
                 session_dir: Optional[str] = None, tools: Optional[Mapping[str, Tool]] = None, **ignored: Any):
        if not providers.drives(type(self), provider):
            raise ValueError(f"{type(self).__name__} drives only {', '.join(providers.providers_of(type(self)))}, not {provider!r}")
        if config is None:
            if not root:
                raise ValueError("no config: pass config=, or root=, the one folder the loop works in")
            config = SubprocessConfig(working_dir=root)
        self.cfg = config
        self.provider = providers.normalise(provider) or "anthropic"
        self.tier = tier or DEFAULT_TIER
        self.settings_source = settings
        self.instructions = instructions
        self.injected = complete
        self.model_translator = model_translator
        self.model = (model_for or providers.model_for)(self.provider, self.tier)
        self.tier_model = self.model
        self.uses_deep_model = True
        self.sandbox = bool(sandbox)
        self.review = review      # True: review written text when the code check finds something; "prose": every written text; False: never
        self.session_dir = session_dir
        self.tools = dict(tools) if tools else None
        self.running: Dict[str, "queue.Queue[str]"] = {}   # run or session id -> the messages waiting for that run
        self.running_lock = threading.Lock()

    # --- steering ----------------------------------------------------------------------------------------------------------------

    def steer(self, message: str, *, run_id: Optional[str] = None, timeout: float = 10.0) -> bool:
        """Hand ``message`` to a RUNNING session from any thread: the loop shows it to the model before its next call. ``run_id`` picks the run
        (its run id or session id); omitted, the only running session. False when no such run is active (or the message is empty). ``timeout`` is
        kept for the signature of the other runners; putting a message never waits."""
        if not str(message or "").strip():
            return False
        with self.running_lock:
            if run_id is not None:
                inbox = self.running.get(run_id)
            else:
                distinct = {id(q): q for q in self.running.values()}
                inbox = next(iter(distinct.values())) if len(distinct) == 1 else None
            if inbox is None:
                return False
            inbox.put(str(message))
            return True

    # --- sessions ----------------------------------------------------------------------------------------------------------------

    def session_path(self, session_id: str) -> Optional[str]:
        folder = self.session_dir or private_directory(SESSION_FOLDER)
        if not folder:
            return None
        os.makedirs(folder, exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id).lstrip(".") or "session"
        return os.path.join(folder, name + ".json")

    def load_session(self, session_id: str) -> Optional[LoopState]:
        """The saved state of ``session_id``, or None (logged) when there is none or it cannot be read."""
        try:
            path = self.session_path(session_id)
            if not path or not os.path.exists(path):
                log.info("no saved session %s: starting fresh", session_id)
                return None
            with open(path, encoding="utf-8") as handle:
                return LoopState.from_json(handle.read())
        except (OSError, ValueError) as error:
            log.warning("saved session %s cannot be read (%s): starting fresh", session_id, error)
            return None

    def save_session(self, session_id: str, state: LoopState) -> None:
        try:
            path = self.session_path(session_id)
            if not path:
                return
            temporary = f"{path}.{uuid.uuid4().hex[:8]}.tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                handle.write(state.to_json())
            os.replace(temporary, path)
        except OSError as error:
            log.warning("could not save session %s: %s", session_id, error)

    # --- settings ----------------------------------------------------------------------------------------------------------------

    def goal_settings(self) -> GoalSettings:
        return resolve_goal_settings(self.settings_source)

    def child_environment(self, settings: GoalSettings) -> Optional[Dict[str, str]]:
        """The environment commands run in, or None to inherit when the settings carry none."""
        env = dict(settings.environment() or {})
        if not env:
            return None
        if self.cfg.extra_path_dirs:
            env["PATH"] = os.pathsep.join(list(self.cfg.extra_path_dirs) + [env.get("PATH", "")])
        return env

    # --- the completion ----------------------------------------------------------------------------------------------------------

    def completion(self, model: str, settings: GoalSettings, usage: Dict[str, float]) -> Callable[[str, str], str]:
        """``complete(system, prompt)``: the injected function, or the Claude CLI provider built now and called as a pure completion. ``usage``
        gains the cost and tokens of each call."""
        if self.injected is not None:
            return self.injected
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
        configured = (self.cfg.claude_path or "").strip() or "claude"
        has_environment = bool(settings.environment())
        engine = ClaudeCliProvider(claude_path=configured, extra_path_dirs=list(self.cfg.extra_path_dirs or []) or None,
                                   environment=settings.environment if has_environment else None)

        def complete(system: str, prompt: str) -> str:
            cost, tokens_in, tokens_out = float(engine.cost_usd or 0.0), int(engine.tokens_in or 0), int(engine.tokens_out or 0)
            text = engine.answer([{"role": "user", "content": prompt}], model=model, system=system)
            used_in, used_out = int(engine.tokens_in or 0) - tokens_in, int(engine.tokens_out or 0) - tokens_out
            spent = float(engine.cost_usd or 0.0) - cost
            usage["tokens"] += used_in + used_out
            usage["cost"] += spent if spent > 0 else price(self.provider, model, used_in, used_out)
            return text
        return complete

    # --- the run -----------------------------------------------------------------------------------------------------------------

    def work(self, goal: str, *, context: str = "", working_dir: Optional[str] = None, max_calls: int = DEFAULT_CALLS,
             model: Optional[str] = None, emit: Optional[Callable[..., None]] = None, cancel_check: Optional[Callable[[], bool]] = None,
             run_id: Optional[str] = None, session_id: Optional[str] = None,
             resume_session_id: Optional[str] = None) -> Tuple[LoopResult, Dict[str, float], str]:
        """One loop on ``goal``: ``(the loop's result, {"cost", "tokens"}, "" or why it stopped early: "timeout" / "cancelled")``. With a
        ``session_id`` the state is saved there after every call, and the state saved under ``resume_session_id`` starts the loop. Raises only
        what a bad setting raises; ``run_goal`` catches it."""
        settings = self.goal_settings()
        run_model = (model or self.model or "") if self.uses_deep_model else (self.model or "")
        if self.model_translator is not None and run_model:
            run_model = self.model_translator(run_model) or run_model
        usage: Dict[str, float] = {"cost": 0.0, "tokens": 0}
        started = time.monotonic()
        cap = self.cfg.timeout_seconds or settings.deep_timeout_seconds or DEFAULT_TIMEOUT_SECONDS
        stopped = {"why": ""}

        def cancel() -> bool:
            if cancel_check is not None:
                try:
                    if cancel_check():
                        stopped["why"] = "cancelled"
                        return True
                except Exception:  # noqa: BLE001 -- a failing cancel check does not stop the run
                    pass
            if time.monotonic() - started > cap:
                stopped["why"] = "timeout"
                return True
            return False

        def tell(text: str) -> None:
            if emit is not None:
                emit(ProgressEvent(type=EVENT_EXEC, text=text, data={"run_id": run_id, "phase": "solution_loop"}))

        standing = with_instructions_pack(settings, self.instructions).standing_instructions()
        context_text = "\n\n".join(part.strip() for part in (context, standing or "") if part and part.strip())
        folder = os.path.abspath(working_dir or self.cfg.working_dir)
        wrap = sandbox_wrap(folder) if self.sandbox else ()
        state = self.load_session(resume_session_id) if resume_session_id else None
        save = (lambda kept: self.save_session(session_id, kept)) if session_id else None
        messages: "queue.Queue[str]" = queue.Queue()
        keys = [key for key in (run_id, session_id) if key]

        def inbox() -> List[str]:
            got: List[str] = []
            while True:
                try:
                    got.append(messages.get_nowait())
                except queue.Empty:
                    return got

        with self.running_lock:
            for key in keys:
                self.running[key] = messages
            if not keys:
                keys.append(uuid.uuid4().hex)
                self.running[keys[0]] = messages
        try:
            result = run_loop(goal, working_dir=folder, complete=self.completion(run_model, settings, usage), context=context_text,
                              max_calls=max_calls, depth=1, cancel=cancel, emit=tell if emit is not None else None,
                              command_timeout=max(1.0, min(60.0, float(cap))), environment=self.child_environment(settings), counter=None,
                              wrap=wrap, state=state, save=save, inbox=inbox, tools=self.tools, review=self.review)
        finally:
            with self.running_lock:
                for key in keys:
                    if self.running.get(key) is messages:
                        del self.running[key]
        return result, usage, stopped["why"]

    def run_goal(self, *, goal: str, brief: str = "", model: Optional[str] = None, max_turns: Optional[int] = None,
                 emit: Optional[Callable[..., None]] = None, context_preamble: Optional[str] = None, run_id: Optional[str] = None,
                 working_dir: Optional[str] = None, cancel_check: Optional[Callable[[], bool]] = None,
                 resume_session_id: Optional[str] = None, **ignored: Any) -> DeepResult:
        """Run the goal (``brief`` when given, else ``goal``) as one loop of at most ``max_turns`` model calls (15 when unset). ``model`` is used
        in place of the arm's tier model. The wall-clock cap stops the run between calls. ``resume_session_id`` continues a saved session (a
        missing or unreadable one starts fresh); the result's ``session_id`` names the session file the run kept. Never raises."""
        try:
            run_model = model or self.model
            if not run_model and self.injected is None:
                return DeepResult(met=False, launch_failed=True, error=f"no {self.tier} model is chosen for the provider {self.provider} in the tier registry")
            preamble = self.cfg.context_preamble if context_preamble is None else context_preamble
            session_id = resume_session_id or run_id or uuid.uuid4().hex
            result, usage, why = self.work(brief or goal, context=preamble or "", working_dir=working_dir, max_calls=int(max_turns or DEFAULT_CALLS),
                                           model=model, emit=emit, cancel_check=cancel_check, run_id=run_id, session_id=session_id,
                                           resume_session_id=resume_session_id)
            deep = self.deep_result(result, usage, why, run_model or "")
            deep.session_id = session_id
            return deep
        except Exception as e:  # noqa: BLE001 -- the DeepRunner port never raises
            log.error("%s failed unexpectedly: %s: %s", type(self).__name__, type(e).__name__, e, exc_info=True)
            return DeepResult(met=False, error=f"The deep worker failed unexpectedly: {type(e).__name__}: {e}")

    def deep_result(self, result: LoopResult, usage: Mapping[str, float], why: str, model: str) -> DeepResult:
        error = result.error
        if why == "timeout":
            error = "The run passed its time limit and was stopped."
        elif why == "cancelled":
            error = "The run was stopped on request."
        decision_id = extract_escalation_id(result.report or "", self.goal_settings().escalation_marker)
        if decision_id:      # the worker raised a decision for a person: the run is not met, and the consumer follows the decision
            return DeepResult(met=False, output=result.report, decision_id=decision_id, cost_usd=float(usage.get("cost", 0.0)),
                              tokens=int(usage.get("tokens", 0)), model=model or None, resolved_model=model or None,
                              changes_landed=len(result.changed), changed_nothing=not result.changed)
        return DeepResult(met=result.met, output=result.report, error=error or None, cost_usd=float(usage.get("cost", 0.0)),
                          tokens=int(usage.get("tokens", 0)), model=model or None, resolved_model=model or None,
                          cancelled=why == "cancelled", limit_hit="call limit" in error, exhausted="call limit" in error,
                          changes_landed=len(result.changed), changed_nothing=not result.changed,
                          observations=[f"changed {path}" for path in result.changed], observations_reported=True)


def price(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    """The list price of the tokens, 0.0 when the model is not priced (the provider reported no cost of its own)."""
    from hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner import list_price
    try:
        return list_price(provider, model, tokens_in, tokens_out)
    except Exception:  # noqa: BLE001 -- a missing price table must not fail a finished run
        return 0.0


def brief_goal(brief: Mapping[str, Any]) -> str:
    """The goal text of a solution-worker brief (``work_solution``): the task, what the parent handed down, the milestone, the frame, the
    children's reports and, on a rework, what the check found missing."""
    lines: List[str] = []
    for label, key in (("Task", "task"), ("Handed to you", "handed"), ("Milestone to reach", "milestone"), ("Solution", "name")):
        if brief.get(key):
            lines.append(f"{label}: {brief[key]}")
    if brief.get("frame"):
        lines.append(f"Frame:\n{brief['frame']}")
    reports = [str(r) for r in (brief.get("reports") or []) if r]
    if reports:
        lines.append("Reports from the parts below this one:\n" + "\n\n".join(reports))
    if brief.get("missing"):
        lines.append(f"The last attempt (round {int(brief.get('round') or 2) - 1}) fell short: {brief['missing']}\nFix exactly that.")
    return "\n\n".join(lines)


def as_solution_worker(runner: SolutionLoopRunner, working_dir: str, *, max_calls: int = DEFAULT_CALLS,
                       cancel: Optional[Callable[[], bool]] = None) -> Callable[[Mapping[str, Any]], str]:
    """A ``work`` callable for ``solution_workers.work_solution``: one loop per brief, in ``working_dir``, returning the loop's report (with the
    reason appended when the loop did not finish)."""
    def work(brief: Mapping[str, Any]) -> str:
        result, _usage, _why = runner.work(brief_goal(brief), working_dir=working_dir, max_calls=max_calls, cancel_check=cancel)
        if result.met:
            return result.report
        return (result.report + "\n" if result.report else "") + f"(not finished: {result.error})"
    return work
