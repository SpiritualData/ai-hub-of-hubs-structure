"""The loop's overseer plumbing: spend metrics, digest, background consult, collect and late follow-up.

A mixin for a loop class. It reads only what ``OverseeHost`` names: a config view with the ``overseer_*`` and budget fields, a
provider, a tier registry, an optional escalation sink, and four hooks the host supplies (how an observation is summarized,
how a digest is built, how the overseer is consulted, how a late human escalation is raised). The overseer's prompt, its
digest wording and the escalation's shape are the host's.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import Future, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional, Tuple

from hubofhubs.ports.deep import ProgressEvent
from hubofhubs.ports.events import EVENT_OVERSEER
from hubofhubs.ports.scope import ScopedThreadPoolExecutor as ThreadPoolExecutor
from hubofhubs.risk import OverseerSignal

from .plan import PlanDecision
from .turn import Emitter
from .watch import worth_a_look


class OverseeHost:
    """What the mixin reads off the loop class that carries it (a contract to read, not a seat; the host does not inherit it)."""

    cfg: Any          # max_steps, max_elapsed_seconds, max_gathered_chars, planner_tier, overseer_tier,
                      # overseer_digest_char_budget, overseer_gate_min_consecutive_reads, overseer_gate_repeat_plan,
                      # overseer_gate_spend_fraction, overseer_background_finish_timeout_seconds
    provider: Any     # may carry tokens_in and tokens_out
    registry: Any     # resolve_tier(name) -> model id
    escalation: Any   # None, or a sink the host's hook knows how to use

    def get_provider_for_model(self, model: str) -> Any: ...
    def oversee_summarize_observation(self, observation: Dict[str, Any]) -> str: ...
    def oversee_digest(self, **fields: Any) -> str: ...
    def oversee_consult(self, provider: Any, model: str, digest: str) -> OverseerSignal: ...
    def oversee_escalate_late(self, reason: Optional[str], scope_id: Optional[str]) -> None: ...


class OverseeMixin:
    """The overseer: spend metrics, digest, submit, collect and finish in the background."""

    def spend_metrics(self, gathered: List[Dict[str, Any]], started: float) -> Tuple[int, int, float]:
        """Cheap, pure metrics shared by the digest builder and the pre-filter gate, computed once so they are never
        duplicated: ``(gathered_chars, consecutive_reads, elapsed_seconds)``. Never raises."""
        gathered_chars = 0
        consecutive_reads = 0
        try:
            gathered_chars = sum(len(o.get("text", "")) + len(str(o.get("hits", "")))
                                 for o in gathered if isinstance(o, dict))
            consecutive_reads = sum(1 for o in gathered
                                    if isinstance(o, dict) and o.get("kind") in ("read", "grep"))
        except Exception:  # noqa: BLE001
            pass
        elapsed_seconds = 0.0
        try:
            elapsed_seconds = time.monotonic() - started
        except Exception:  # noqa: BLE001
            pass
        return gathered_chars, consecutive_reads, elapsed_seconds

    def operation_lines(self, gathered: List[Dict[str, Any]], window: int = 8) -> Tuple[List[str], int]:
        """The ``operations``/``operations_total`` pair for the digest: each entry tagged with its observation ``kind``
        (read/grep/query/...), summarized by the host's one-line summarizer so the full observation bodies never reach the
        overseer. ``operations_total`` is the TRUE count of operations so far (``operations`` may be a trailing window).
        Never raises."""
        try:
            ops_all = [o for o in gathered if isinstance(o, dict)]
            recent = ops_all[-window:]
            lines = [f"[{o.get('kind') or 'op'}] {self.oversee_summarize_observation(o)}" for o in recent]
            return lines, len(ops_all)
        except Exception:  # noqa: BLE001
            return [], 0

    def build_oversee_digest(self, *, user_message: str, goal_condition: Optional[str] = None,
                             step: int, plan: Optional[PlanDecision],
                             gathered: List[Dict[str, Any]], started: float,
                             draft_answer: Optional[str] = None,
                             quality_standards: Optional[str] = None,
                             recent_conversation: Optional[List[str]] = None,
                             prior_escalations: Optional[List[str]] = None) -> str:
        """The cheap, capped overseer digest for the current run state. Pure and synchronous (no network): it only
        summarizes what is already in hand, so it is safe to run inline right before submitting the ONE provider call to a
        background thread. Never raises."""
        cfg = self.cfg
        gathered_chars, consecutive_reads, elapsed_seconds = self.spend_metrics(gathered, started)
        operations, operations_total = self.operation_lines(gathered)
        tokens_in = getattr(self.provider, "tokens_in", 0) or 0
        tokens_out = getattr(self.provider, "tokens_out", 0) or 0
        return self.oversee_digest(
            user_message=user_message,
            goal_condition=goal_condition,
            step=step,
            max_steps=cfg.max_steps,
            plan_action=(plan.action if plan else ""),
            plan_rationale=(plan.rationale if plan else ""),
            plan_goal=(plan.goal if plan else ""),
            recent_conversation=recent_conversation,
            prior_escalations=prior_escalations,
            operations=operations,
            operations_total=operations_total,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            elapsed_seconds=elapsed_seconds,
            max_elapsed_seconds=cfg.max_elapsed_seconds,
            gathered_chars=gathered_chars,
            max_gathered_chars=cfg.max_gathered_chars,
            consecutive_reads=consecutive_reads,
            draft_answer=draft_answer,
            quality_standards=quality_standards,
            char_budget=cfg.overseer_digest_char_budget,
        )

    def submit_oversee(self, executor: ThreadPoolExecutor, *, user_message: str, step: int,
                       plan: Optional[PlanDecision], gathered: List[Dict[str, Any]],
                       started: float, goal_condition: Optional[str] = None,
                       draft_answer: Optional[str] = None,
                       quality_standards: Optional[str] = None,
                       recent_conversation: Optional[List[str]] = None,
                       prior_escalations: Optional[List[str]] = None,
                       prev_plan_signature: Optional[Any] = None,
                       gate: bool = True) -> Optional[Dict[str, Any]]:
        """FIRE-AND-FORGET consult: build the cheap digest synchronously, then submit the ONE overseer provider call to a
        BACKGROUND thread and return a pending-consultation record WITHOUT waiting. Recording and emitting happen later in
        ``collect_oversee`` (when the result is applied), so the run's signals only ever hold consults that actually
        completed. Never raises: on any setup failure, OR when ``gate=True`` and the cheap pre-filter says this step is not
        worth a look, it returns ``None`` (the caller proceeds as if the overseer were off or not yet due). ``gate=False``
        (the one-time answer checkpoint) always submits, subject only to the caller's own bookkeeping.
        """
        try:
            gathered_chars, consecutive_reads, elapsed_seconds = self.spend_metrics(gathered, started)
            if gate:
                plan_repeats_prev = bool(
                    prev_plan_signature is not None and plan is not None
                    and (plan.action, plan.goal) == prev_plan_signature
                )
                if not worth_a_look(
                    consecutive_reads=consecutive_reads,
                    plan_repeats_prev=plan_repeats_prev,
                    elapsed_seconds=elapsed_seconds,
                    max_elapsed_seconds=self.cfg.max_elapsed_seconds,
                    gathered_chars=gathered_chars,
                    max_gathered_chars=self.cfg.max_gathered_chars,
                    min_consecutive_reads=self.cfg.overseer_gate_min_consecutive_reads,
                    gate_repeat_plan=self.cfg.overseer_gate_repeat_plan,
                    spend_fraction=self.cfg.overseer_gate_spend_fraction,
                ):
                    return None
            digest = self.build_oversee_digest(
                user_message=user_message, goal_condition=goal_condition, step=step, plan=plan,
                gathered=gathered, started=started, draft_answer=draft_answer,
                quality_standards=quality_standards, recent_conversation=recent_conversation,
                prior_escalations=prior_escalations)
            model = self.registry.resolve_tier(self.cfg.overseer_tier)
            provider = self.get_provider_for_model(model)
            # FALLBACK: a consult that comes back DEGRADED (provider error or unusable response, not a real verdict) retries
            # ONCE at the planner tier. Without this, a deployment whose overseer tier resolves to a model the wired
            # provider cannot serve has a permanently silent overseer that looks exactly like a healthy one. Both calls run
            # in the SAME background worker, so the loop still never blocks.
            fb_model: Optional[str] = None
            try:
                fb_model = self.registry.resolve_tier(self.cfg.planner_tier)
            except Exception:  # noqa: BLE001  no fallback tier, primary consult only
                fb_model = None
            fb_provider = self.get_provider_for_model(fb_model) if fb_model else None

            def consult() -> OverseerSignal:
                sig = self.oversee_consult(provider, model, digest)
                if sig.degraded and fb_model and fb_model != model and fb_provider is not None:
                    return self.oversee_consult(fb_provider, fb_model, digest)
                return sig

            # The consult itself never raises (it degrades to proceed), so the worker is safe.
            future: Future = executor.submit(consult)
            return {"future": future, "step": step, "plan": plan}
        except Exception:  # noqa: BLE001  submission failure must never break the run
            return None

    def collect_oversee(self, pending: Optional[Dict[str, Any]], *,
                        signals: List[Dict[str, Any]], emit: Optional[Emitter],
                        timeout: float = 0.0) -> Optional[OverseerSignal]:
        """Poll a previously-submitted consult. Returns its ``OverseerSignal`` if it has RESOLVED, recording it into
        ``signals`` and emitting an EVENT_OVERSEER (so late-resolving consults are still recorded). Returns ``None`` when it
        has NOT resolved yet (the caller proceeds as if ``proceed``).

        ``timeout=0.0`` is a pure, non-blocking ``future.done()`` check that NEVER blocks. A small positive ``timeout`` lets
        it briefly wait for a still-running consult; on timeout it returns ``None`` (proceed), so it can never hang the run.
        Never raises.
        """
        if not pending:
            return None
        future = pending.get("future")
        step = pending.get("step", 0)
        plan = pending.get("plan")
        if future is None:
            return None
        try:
            if timeout and timeout > 0:
                try:
                    signal = future.result(timeout=timeout)
                except FuturesTimeoutError:
                    return None  # still running -> proceed, re-check next opportunity
            else:
                if not future.done():
                    return None  # not resolved yet -> proceed, never block
                signal = future.result()
        except Exception:  # noqa: BLE001  a worker failure degrades to proceed
            signal = OverseerSignal("proceed")
        if not isinstance(signal, OverseerSignal):
            signal = OverseerSignal("proceed")
        signals.append({"signal": signal.signal, "hint": signal.hint,
                        "reason": signal.reason, "step": step})
        if emit is not None:
            try:
                emit.emit(ProgressEvent(
                    type=EVENT_OVERSEER, step=step,
                    action=(plan.action if plan else None),
                    text=(signal.reason or None),
                    data={"signal": signal.signal, "hint": signal.hint}))
            except Exception:  # noqa: BLE001
                pass
        return signal

    def finish_oversee_in_background(self, pending: Optional[Dict[str, Any]], *,
                                     emit: Optional[Emitter],
                                     scope_id: Optional[str] = None,
                                     brainstorm_active: bool = False) -> None:
        """Fire-and-forget continuation for the one-time answer checkpoint: when that consult has NOT resolved by the time
        the answer ships, the answer is returned immediately and this BACKGROUND daemon thread waits (bounded by
        ``overseer_background_finish_timeout_seconds``) for it, then applies a BEST-EFFORT, non-authoritative follow-up,
        never mutating the already-returned result:

          - ``escalate_human``: the host's ``oversee_escalate_late`` raises a real human escalation through its durable
            channel, so a human is notified even though the stream that served this turn's answer may already be closed.
          - ``redirect`` / ``escalate_deep``: recorded via a late EVENT_OVERSEER (data includes ``"late": True``) so a
            STILL-LISTENING consumer can see it, and so a caller that persists these events can pass them forward as prior
            escalations on the NEXT turn. Deliberately does NOT launch a new deep execution: nothing is left to receive its
            result once the original caller has moved on.
          - ``proceed`` / a timeout: nothing to do.

        ``brainstorm_active`` (the latch's value when the answer shipped) mirrors the synchronous rule: while a brainstorm
        turn is active, overseer escalations may not ADD actions, so a late ``escalate_human`` raises nothing (the late event
        is still emitted as telemetry).

        Never raises. Runs in a daemon thread so it cannot keep the process alive or crash on interpreter shutdown; started
        best-effort (a failure to even start the thread is swallowed).
        """
        if not pending:
            return
        future = pending.get("future")
        step = pending.get("step", 0)
        plan = pending.get("plan")
        if future is None:
            return

        def background() -> None:
            try:
                signal = future.result(timeout=self.cfg.overseer_background_finish_timeout_seconds)
            except Exception:  # noqa: BLE001  timeout or worker failure: nothing to finish
                return
            if not isinstance(signal, OverseerSignal) or signal.signal == "proceed":
                return
            if emit is not None:
                try:
                    emit.emit(ProgressEvent(
                        type=EVENT_OVERSEER, step=step,
                        action=(plan.action if plan else None),
                        text=(signal.reason or None),
                        data={"signal": signal.signal, "hint": signal.hint, "late": True}))
                except Exception:  # noqa: BLE001
                    pass
            if (signal.signal == "escalate_human" and not brainstorm_active
                    and self.escalation is not None):
                try:
                    self.oversee_escalate_late(signal.reason, scope_id)
                except Exception:  # noqa: BLE001
                    pass

        try:
            threading.Thread(target=background, daemon=True).start()
        except Exception:  # noqa: BLE001
            pass
