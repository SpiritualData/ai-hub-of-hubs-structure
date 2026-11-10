"""Ceilings on money and time for the runners of Delegated Agent Sessions, and the one seam through which the hub's own iteration is decided.

Role: a run the hub itself keeps going (resuming a session after its own check, nudging a loop again, re-working a part of the solution hierarchy)
must never go on forever by omission. Every runner that shares this module has a default ceiling on spend and on wall time (high, so ordinary work never meets it),
an explicit ``UNLIMITED`` for a caller that chooses none, a soft limit (at ``SOFT_FRACTION`` of either ceiling) at which the session is steered once to a safe stopping
point, and a hard limit at which it is stopped the way a person's stop is, with the work kept and resumable. A person's own session is judged by none of the stop
logic here: it runs until a ceiling the person can raise, as Claude Code's does; only the hub's own iteration is put to Goal Completion's stop decision.

Shared by ``native_runner`` (the model's own tool loop), ``stream_runner`` (the steerable Claude Code session) and ``solution_loop_runner`` (the hub's text loop).
Standard library plus the hub."""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from hubofhubs.the_world.tools.events import EVENT_STATUS
from hubofhubs.the_world.tools.delegated_agent_sessions.control import ControlMessage, RunControl
from hubofhubs.the_world.tools.delegated_agent_sessions.session import claude_project_bases

UNLIMITED = "unlimited"        # the only way to run with no ceiling on a dimension: the caller says so, never by omission
DEFAULT_CEILING_USD = 20.0     # about 900 times the dearest hard case measured at the fast tier ($0.0225); a consumer can raise or lower it
DEFAULT_CEILING_SECONDS = 4 * 3600.0   # about 160 times the longest hard case measured (88 s)
SOFT_FRACTION = 0.8            # the share of either ceiling at which the session is asked to reach a safe stopping point
BACKSTOP_SECONDS = 120.0       # how long past the time ceiling the CLI's own wall-clock cap waits for the graceful stop
WRAP_UP_MESSAGE = ("The time or spend allowed for this run is nearly used. Reach the next natural safe stopping point: finish the step in hand, leave every "
                   "file and any store in a consistent state, do not start new work, and report what is done, what is left and how to resume.")
MAX_RESUMES = 5   # a bound on the hub's own iteration whatever an injected decision says; the person's own session is not capped by it


def ceiling_of(value: Union[float, str, None], name: str) -> Optional[float]:
    """A ceiling as a positive number, or None for the explicit ``UNLIMITED``. Omission never means unlimited: the defaults are on."""
    if value == UNLIMITED:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number or UNLIMITED")
    return float(value)


def soft_fraction_of(value: float) -> float:
    if not 0.0 < float(value) < 1.0:
        raise ValueError("soft_fraction must be between 0 and 1")
    return float(value)


def default_should_continue(facts: Mapping[str, Any]) -> Dict[str, Any]:
    """The hub's deterministic default for iteration the person did not ask for (a resume after its own check): at most one, only for a code finding, never when
    a ceiling is reached. ``facts`` is plain data: ``spend_usd``, ``turns``, ``resumes``, ``findings`` (the code findings), ``changed_outcome``
    (None before a resume, else whether the last resume changed the findings), ``elapsed_seconds``, ``ceiling_usd``, ``ceiling_seconds``, ``ceiling_turns``
    (None when unlimited) and ``soft_fraction``. A resume starts new work, so it is refused once the soft share of either ceiling is used.
    Returns ``{"continue": bool, "reason": str}``. It is the fallback of ``stop_aware``, which asks Goal Completion instead when a stop decision is assembled."""
    if not facts.get("findings"):
        return {"continue": False, "reason": "no_code_finding"}
    if int(facts.get("resumes") or 0) >= 1:
        return {"continue": False, "reason": "resume_limit"}
    usd, turns, seconds = facts.get("ceiling_usd"), facts.get("ceiling_turns"), facts.get("ceiling_seconds")
    soft = float(facts.get("soft_fraction") or SOFT_FRACTION)
    if usd is not None and float(facts.get("spend_usd") or 0.0) >= float(usd) * soft:
        return {"continue": False, "reason": "ceiling_spend"}
    if seconds is not None and float(facts.get("elapsed_seconds") or 0.0) >= float(seconds) * soft:
        return {"continue": False, "reason": "ceiling_time"}
    if turns is not None and int(facts.get("turns") or 0) >= int(turns):
        return {"continue": False, "reason": "ceiling_turns"}
    return {"continue": True, "reason": "code_finding"}


def decision_of(raw: Any) -> Tuple[bool, str]:
    """A decision as ``(continue, reason)`` from a bool, a ``(bool, reason)`` pair or a mapping with ``continue`` and ``reason``."""
    if isinstance(raw, Mapping):
        return bool(raw.get("continue")), str(raw.get("reason") or "")
    if isinstance(raw, (tuple, list)) and raw:
        return bool(raw[0]), str(raw[1]) if len(raw) > 1 else ""
    return bool(raw), "" if raw else "declined"


# --- the stop decision of Goal Completion, reached through the hub's own resolution ------------------------------------------------------

def selected_stop_decider() -> Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]]:
    """Goal Completion's ``decide_stop`` through the hub's own resolution (see ``stop_rule.selected_stop_decider``), or None when none is assembled."""
    from hubofhubs.the_intelligence.critical_thinking.goal_completion.stop_rule import selected_stop_decider as resolve
    return resolve()


def history_of_rounds(rounds: Sequence[Mapping[str, Any]], facts: Mapping[str, Any], *, goal: str = "", done_standard: str = "",
                      stated: Optional[Mapping[str, Any]] = None, policy: Optional[Mapping[str, Any]] = None, needs_human: str = "") -> Dict[str, Any]:
    """An iteration history for Goal Completion from the rounds of a run. Each round is ``{"findings": int, "spend_usd": cumulative, "elapsed_seconds": cumulative,
    "changed": int}``: the metric is the count of findings (lower is better, zero is the target), the round is met when none is left, and the cost of a round is the
    difference of the cumulative figures."""
    iterations, before_spend, before_time = [], 0.0, 0.0
    for round_ in rounds:
        spend, seconds = float(round_.get("spend_usd") or 0.0), float(round_.get("elapsed_seconds") or 0.0)
        count = int(round_.get("findings") or 0)
        iterations.append({"verdict": count == 0, "changed": int(round_.get("changed") or 0), "metric": float(count), "missing": ["a finding"] * count,
                           "spend_usd": max(spend - before_spend, 0.0), "seconds": max(seconds - before_time, 0.0)})
        before_spend, before_time = spend, seconds
    return {"goal": goal, "done_standard": done_standard, "iterations": iterations, "metric": {"better": "lower", "target": 0.0},
            "ceiling": {"spend_usd": facts.get("ceiling_usd"), "seconds": facts.get("ceiling_seconds"), "soft_fraction": facts.get("soft_fraction") or SOFT_FRACTION},
            "stated": dict(stated or {}), "policy": dict(policy or {}), "needs_human": needs_human}


def stop_aware(decider: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None, *, stated: Optional[Mapping[str, Any]] = None,
               policy: Optional[Mapping[str, Any]] = None, goal: str = "", done_standard: str = "",
               fallback: Callable[[Mapping[str, Any]], Any] = default_should_continue) -> Callable[[Mapping[str, Any]], Dict[str, Any]]:
    """A ``should_continue`` that asks Goal Completion's stop decision. The facts it is given carry ``rounds`` (see ``history_of_rounds``); without rounds or without a
    decider (none selected or assembled) the ``fallback`` decides, so a hub with no stop decision behaves as before. What the person stated and the policy are plain
    inputs the consumer resolved from Consciousness (``resolve_stop_limits``); the reason returned is the decision's code, and the decision itself is in ``decision``."""
    def decide(facts: Mapping[str, Any]) -> Dict[str, Any]:
        chosen = decider if decider is not None else selected_stop_decider()
        rounds = facts.get("rounds")
        if chosen is None or not rounds or not facts.get("findings"):      # nothing to iterate on, or no stop decision assembled: the fallback decides
            return dict(decision_dict(fallback(facts)))
        verdict = chosen(history_of_rounds(rounds, facts, goal=goal, done_standard=done_standard, stated=stated, policy=policy))
        return {"continue": bool(verdict.get("continue", verdict.get("decision") == "continue")), "reason": str(verdict.get("code") or verdict.get("decision") or ""),
                "decision": str(verdict.get("decision") or ""), "left": str(verdict.get("left") or "")}
    return decide


def decision_dict(raw: Any) -> Dict[str, Any]:
    go, reason = decision_of(raw)
    return {"continue": go, "reason": reason}


# --- the ceilings of one run ----------------------------------------------------------------------------------------------------------

ACTIVE = threading.local()      # the watch of the run in this thread, so a runner that calls its parent's run does not start a second one


def active_watch() -> Optional["LimitWatch"]:
    return getattr(ACTIVE, "watch", None)


class LimitWatch:
    """The ceilings of ONE run: spend (the settled cost of finished sessions, or ``spend_of()`` when that is more, since the CLI reports cost only when a session ends)
    and wall time. ``wrap`` adds them to a ``RunControl``: at the soft limit the session is steered once to a safe stopping point, at the hard limit the run is stopped the way
    a person's stop is, keeping the session. The caller's own messages and stop still pass."""

    def __init__(self, ceiling_usd: Optional[float], ceiling_seconds: Optional[float], soft_fraction: float = SOFT_FRACTION,
                 spend_of: Optional[Callable[[], float]] = None, emit: Optional[Callable[[Any], None]] = None, log: Any = None, throttle: float = 3.0):
        self.ceiling_usd, self.ceiling_seconds, self.soft_fraction = ceiling_usd, ceiling_seconds, soft_fraction
        self.spend_of, self.emit, self.log, self.throttle = spend_of, emit, log, throttle
        self.started = time.monotonic()
        self.softened, self.hard, self.settled = False, "", 0.0
        self.estimated_at, self.estimate = 0.0, 0.0
        self.live: Dict[str, float] = {}      # the running calls' spend so far, by call, for a runner that knows its own spend (a text loop and its helpers)
        self.lock = threading.Lock()

    def __enter__(self) -> "LimitWatch":
        ACTIVE.watch = self
        return self

    def __exit__(self, *exc: Any) -> None:
        ACTIVE.watch = None

    @property
    def limited(self) -> bool:
        return self.ceiling_usd is not None or self.ceiling_seconds is not None

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def track(self, key: str, spent: float) -> None:
        """The spend so far of the call ``key``, read by ``spend`` until ``settle`` closes the call."""
        with self.lock:
            self.live[key] = float(spent)

    def settle(self, key: str, spent: float) -> None:
        with self.lock:
            self.live.pop(key, None)
            self.settled += float(spent)

    def spend(self) -> float:
        if self.spend_of is None:
            with self.lock:
                return self.settled + sum(self.live.values())
        now = time.monotonic()
        if self.spend_of is not None and now - self.estimated_at >= self.throttle:
            self.estimated_at = now
            try:
                self.estimate = float(self.spend_of() or 0.0)
            except Exception:  # noqa: BLE001 -- an estimate that fails is no estimate
                self.estimate = 0.0
        return max(self.settled, self.estimate)

    def state(self) -> Tuple[str, str]:
        """``("ok" | "soft" | "hard", what)`` where ``what`` names the ceiling reached (``spend`` or ``time``)."""
        reached: List[Tuple[float, str]] = []
        if self.ceiling_seconds is not None:
            reached.append((self.elapsed() / self.ceiling_seconds, "time"))
        if self.ceiling_usd is not None:
            reached.append((self.spend() / self.ceiling_usd, "spend"))
        share, what = max(reached, default=(0.0, ""))
        return ("hard" if share >= 1.0 else "soft" if share >= self.soft_fraction else "ok"), what if share >= self.soft_fraction else ""

    def soften(self) -> bool:
        """True once, when the soft limit is first reached: the caller then hands the session ``WRAP_UP_MESSAGE``."""
        if not self.softened and not self.hard and self.state()[0] != "ok":
            self.softened = True
            if self.log is not None:
                self.log.info("the soft limit is reached; the session is asked to reach a safe stopping point")
            if self.emit is not None:
                from hubofhubs.the_world.tools.deep import ProgressEvent
                try:
                    self.emit(ProgressEvent(type=EVENT_STATUS, text="The soft limit is reached: the session is asked to reach a safe stopping point.",
                                            data=dict(phase="soft_limit", ceiling_usd=self.ceiling_usd, ceiling_seconds=self.ceiling_seconds)))
                except Exception:  # noqa: BLE001 -- a sink that fails never stops the run
                    pass
            return True
        return False

    def hard_reached(self) -> bool:
        state, what = self.state()
        if state == "hard":
            self.hard = what
        return state == "hard"

    def wrap(self, control: Optional[RunControl], poll_seconds: float = 1.0) -> Optional[RunControl]:
        if not self.limited:
            return control
        mine = control or RunControl()

        def claim() -> List[ControlMessage]:
            messages = list(mine.claim_inputs() or [])
            if self.soften():
                messages.append(ControlMessage(id="hub-wrap-up-" + uuid.uuid4().hex[:8], text=WRAP_UP_MESSAGE))
            return messages

        def stop() -> bool:
            return bool(mine.cancel_requested()) or self.hard_reached()

        wrapped = RunControl(claim_inputs=claim, mark_seen=mine.mark_seen, cancel_requested=stop, pause_requested=mine.pause_requested,
                             poll_seconds=min(float(mine.poll_seconds), poll_seconds), label=mine.label)
        return wrapped

    def finish(self, result: Any) -> None:
        """What the caller needs to account for the run and to continue it, on the result: ``spend_usd`` and ``elapsed_seconds`` (when the runner has not set them),
        ``resume_handle`` (the session id) and, when a ceiling shaped the run and nothing else already said why it ended, ``end_reason`` (see ``end_reason``) and,
        for a hard stop, an error that names the session to resume."""
        if getattr(result, "spend_usd", None) is None:
            result.spend_usd = max(float(getattr(result, "cost_usd", 0.0) or 0.0), self.spend())
        if getattr(result, "elapsed_seconds", None) is None:
            result.elapsed_seconds = self.elapsed()
        result.resume_handle = getattr(result, "session_id", None)
        reason = self.end_reason()
        if reason and not getattr(result, "end_reason", None):
            result.end_reason = reason
        if self.hard and getattr(result, "cancelled", False) and not getattr(result, "paused", False):   # the hard limit names itself, not the runner's generic "stopped on request"
            result.error = (f"The run was stopped at its hard limit ({self.hard}). Work already finished is kept; resume session "
                            f"{getattr(result, 'session_id', None)} to continue.")

    def end_reason(self) -> str:
        """Which ceiling shaped the run: ``stopped_at_hard_limit:<what>`` or ``wrapped_up_at_soft_limit``, else ``""``."""
        if self.hard:
            return f"stopped_at_hard_limit:{self.hard}"
        return "wrapped_up_at_soft_limit" if self.softened else ""


# --- what a run has spent, read from the session record ---------------------------------------------------------------------------------

def current_session_file(root: str, since: float, config_dir: Optional[str] = None) -> Optional[str]:
    """The record of the session the run has open in ``root``: the newest of the project's files touched since ``since`` (a monotonic start, taken
    as the last few minutes of wall time). ``None`` when there is none."""
    key = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(root))
    horizon = time.time() - (time.monotonic() - since) - 2.0
    best: Tuple[float, Optional[str]] = (0.0, None)
    for base in claude_project_bases(root, config_dir):
        try:
            for entry in os.scandir(base / key):
                if entry.name.endswith(".jsonl") and entry.stat().st_mtime >= horizon and entry.stat().st_mtime > best[0]:
                    best = (entry.stat().st_mtime, entry.path)
        except OSError:
            continue
    return best[1]


CACHE_WRITE_ONE_HOUR, CACHE_WRITE_FIVE_MINUTES, CACHE_READ = 2.0, 1.25, 0.1   # the provider's multiples of the plain input price for a cached prefix


def estimate_spend(path: Optional[str]) -> float:
    """List-price dollars of the tokens a session's record holds, from the hub's price table: plain input, cache writes (by their lifetime) and cache reads at their
    multiples of the input price, and output. Each model message counts once, however many content blocks the record splits it into. 0.0 for a record that cannot be
    read or a model the table does not price. An estimate that lets a ceiling act before the CLI reports cost; measured against the CLI's own figure it is within 1 percent."""
    if not path:
        return 0.0
    try:
        from hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner import list_price
        last: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        with open(path, encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                message = event.get("message") if event.get("type") == "assistant" else None
                usage = (message or {}).get("usage") or {}
                if usage:
                    last[str(message.get("id") or f"line-{number}")] = (str(message.get("model") or ""), usage)     # the last block of a message holds its final counts
        totals: Dict[str, List[float]] = {}
        for model, usage in last.values():
            written = usage.get("cache_creation") or {}
            hour, five = int(written.get("ephemeral_1h_input_tokens") or 0), int(written.get("ephemeral_5m_input_tokens") or 0)
            if not written:
                five = int(usage.get("cache_creation_input_tokens") or 0)
            got = totals.setdefault(model, [0.0, 0.0])
            got[0] += (int(usage.get("input_tokens") or 0) + CACHE_WRITE_ONE_HOUR * hour + CACHE_WRITE_FIVE_MINUTES * five
                       + CACHE_READ * int(usage.get("cache_read_input_tokens") or 0))
            got[1] += int(usage.get("output_tokens") or 0)
        return sum(list_price("anthropic", model, int(tin), int(tout)) for model, (tin, tout) in totals.items() if model)
    except Exception:  # noqa: BLE001 -- an estimate that fails is no estimate
        return 0.0
