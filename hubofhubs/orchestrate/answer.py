"""Composing answers: a grounded answer, the sub-question fan-out, and the post-work synthesis.

The mixin holds the flow only. Every sentence the model is told and every sentence the person may read as a fallback is in the
``AnswerKit`` the host supplies, with the functions that render the grounding. Nothing here names a consumer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from hubofhubs.act.execution_record import ExecutionRecord
from hubofhubs.ports.model import STEP_REPLY, answer_with_reasoning
from hubofhubs.ports.scope import ScopedThreadPoolExecutor as ThreadPoolExecutor

from .plan import PlanDecision


@dataclass(frozen=True)
class AnswerKit:
    """The consumer's text and renderers for answering. Templates use ``str.format`` fields as noted."""

    reply_voice_system: str                       # the system prompt every reply is written under
    synthesize_after_deep: str                    # fields: request, proposal, result, standard_line
    synthesize_task_report: str                   # same fields: the report of a finished background task
    synthesize_after_queued: str                  # fields: request, proposal, result
    subquestion_focus: str                        # field: sub
    merge_prompt: str                             # fields: message, merged
    merged_part: str                              # fields: q, a
    done_standard_line: str                       # field: standard (inserted when a done-standard is given)
    queued_note: str                              # the fallback sentence after a confirmed hand-off
    report_goal: str                              # field: request (the goal of the claim check)
    none_marker: str                              # said for an empty proposal
    handoff_marker: str                           # said for an empty hand-off output
    grounding_block: Callable[[str, List[Dict[str, Any]], bool], str]
    grounding_tail: Callable[[List[Dict[str, Any]], bool], str]
    grounding_layer: Callable[[str], str]
    layered_blocks: Callable[[str, str, str], Any]   # (persona, context, tail) -> the layers a provider takes
    accepts_layers: Callable[[Any], bool]            # whether a provider's answer call takes layers
    log: Any                                         # the logger the host's loop writes to


class AnsweringMixin:
    """Composing answers. The host carries ``cfg`` (max_subquestions, max_parallel), ``registry``, ``provider``,
    ``get_provider_for_model``, ``answer_kit`` (an ``AnswerKit``) and ``verify_goal`` (the done-check, for the claim check)."""

    def answer_model(self, plan: PlanDecision, default_tier: str, hint: Optional[str] = None) -> str:
        """Resolve the model id for an answer or deep step.

        Precedence (highest to lowest):
          1. ``hint``: a per-run model string passed by the caller. Opaque: the consumer's ModelProvider and ModelRegistry
             interpret it. Unknown tiers degrade gracefully to the registry's default (never raises).
          2. ``plan.model_tier``: the planner's own choice for this step.
          3. ``default_tier``: the caller's compile-time default.
        """
        tier = hint or plan.model_tier or default_tier
        return self.registry.resolve_tier(tier)

    def grounded_answer(self, user_message: str, transcript: str, context_view: str,
                        gathered: List[Dict[str, Any]], model: str, partial: bool,
                        native_blocks: Optional[List[Dict[str, Any]]] = None,
                        rep_preamble: Optional[str] = None,
                        reply_directive: Optional[str] = None) -> str:
        kit = self.answer_kit
        messages = []
        if rep_preamble:
            messages.append({"role": "user", "content": rep_preamble})
        if transcript:
            messages.append({"role": "user", "content": transcript})
        messages.append({"role": "user", "content": kit.grounding_block(context_view, gathered, partial)})
        # The final user message carries the question; when native image blocks are present (an image attachment going to a
        # vision-capable model) they ride along in the SAME message as a content-block list.
        if native_blocks:
            content: List[Dict[str, Any]] = list(native_blocks)
            content.append({"type": "text", "text": user_message})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user_message})
        provider = self.get_provider_for_model(model)
        # The reply voice rides as the system prompt, not as another user turn: it has to sit ABOVE the grounding and
        # transcript blocks (which are phrased as instructions ABOUT the person) so the model answers in its own voice
        # instead of mirroring theirs. Cache-friendly layered shape in addition to the ``messages`` fallback: the persona is
        # the stable head, the grounding context the stable middle, and transcript + this turn's gathered content + the new
        # message the volatile tail. Skipped for a multimodal turn and for a provider without the layered surface, both of
        # which keep the untouched ``messages`` path. ``reply_directive`` is a how-to-reply instruction for this turn; it
        # rides on the SYSTEM prompt, NOT inside the grounding block, which is introduced to the model as material to answer
        # FROM and never mention.
        answer_kwargs: Dict[str, Any] = {
            "model": model,
            "system": (f"{kit.reply_voice_system}\n\n{reply_directive}" if reply_directive
                       else kit.reply_voice_system),
        }
        if not native_blocks and kit.accepts_layers(provider.answer):
            tail_parts: List[str] = []
            if transcript:
                tail_parts.append(transcript)
            tail_parts.append(kit.grounding_tail(gathered, partial))
            tail_parts.append(user_message)
            answer_kwargs["layers"] = kit.layered_blocks(
                rep_preamble or "", kit.grounding_layer(context_view), "\n\n".join(tail_parts))
        return answer_with_reasoning(provider, messages, step=STEP_REPLY, **answer_kwargs)

    def synthesize_after_deep(self, user_message: str, *, prior_answer: str, deep_output: str,
                              transcript: str, model: str,
                              rep_preamble: Optional[str] = None,
                              prompt_template: Optional[str] = None,
                              standard: str = "") -> str:
        """Rewrite the final reply to REPORT what a (deferred) deep run actually did or produced.

        ``prompt_template`` is the report shape: the kit's after-deep reply by default, or its task-report template for a
        finished background task's chat report. ``standard`` is the planner's own done-standard for the work: when given,
        the reply is told to show it met, so a clause such as "confirmed in the reply" is answered in the reply.

        After a deferred deep run, the pre-deep answer is a proposal that usually reads as "shall I proceed?", while the real
        deliverable lives in the deep run's output. This folds that output back into one user-facing reply grounded in what
        was actually done. One model call. Never raises: on any failure it falls back to the deep output itself (the real
        work), and only then to the prior answer, so the person always sees the substance.
        """
        kit = self.answer_kit
        template = prompt_template if prompt_template is not None else kit.synthesize_after_deep
        out = (deep_output or "").strip()
        try:
            prompt = template.format(
                request=user_message,
                proposal=(prior_answer or kit.none_marker).strip()[:4000],
                result=out[:24000],
                standard_line=(kit.done_standard_line.format(standard=standard.strip()[:400])
                               if (standard or "").strip() else ""),
            )
            messages: List[Dict[str, Any]] = []
            if rep_preamble:
                messages.append({"role": "user", "content": rep_preamble})
            if transcript:
                messages.append({"role": "user", "content": transcript})
            messages.append({"role": "user", "content": prompt})
            provider = self.get_provider_for_model(model)
            synthesized = answer_with_reasoning(provider, messages, model=model,
                                                step=STEP_REPLY, system=kit.reply_voice_system)
            if isinstance(synthesized, str) and synthesized.strip():
                return synthesized.strip()
        except Exception:  # noqa: BLE001  synthesis must never break the turn
            kit.log.warning("post-deep synthesis failed; falling back to deep output", exc_info=True)
        return out or (prior_answer or "")

    def synthesize_after_queued(self, user_message: str, *, prior_answer: str,
                                handoff_output: str, transcript: str, model: str,
                                rep_preamble: Optional[str] = None) -> str:
        """Rewrite the reply after a CONFIRMED deferred hand-off (queued deployments).

        The counterpart of ``synthesize_after_deep`` for a deep runner that QUEUED the work as a background task instead of
        executing it: the reply must report the hand-off, never present the work as done. Only called after the enqueue is
        confirmed, so the fallback line may honestly say the work is queued. One model call; never raises.
        """
        kit = self.answer_kit
        try:
            prompt = kit.synthesize_after_queued.format(
                request=user_message,
                proposal=(prior_answer or kit.none_marker).strip()[:4000],
                result=(handoff_output or kit.handoff_marker).strip()[:4000],
            )
            messages: List[Dict[str, Any]] = []
            if rep_preamble:
                messages.append({"role": "user", "content": rep_preamble})
            if transcript:
                messages.append({"role": "user", "content": transcript})
            messages.append({"role": "user", "content": prompt})
            provider = self.get_provider_for_model(model)
            synthesized = answer_with_reasoning(provider, messages, model=model,
                                                step=STEP_REPLY, system=kit.reply_voice_system)
            if isinstance(synthesized, str) and synthesized.strip():
                return synthesized.strip()
        except Exception:  # noqa: BLE001  synthesis must never break the turn
            kit.log.warning("post-queue synthesis failed; falling back to a plain hand-off note", exc_info=True)
        return ((prior_answer or "").strip() + "\n\n" + kit.queued_note).strip()

    def synthesize_task_report(self, request: str, deep_output: str, *,
                               transcript: str = "",
                               rep_preamble: Optional[str] = None,
                               tier: str = "balanced") -> str:
        """PUBLIC: write the finished-work report for a completed background task.

        Used by an executor to fold a deep run's raw output into a message that reads as the AI reporting its own finished
        work, before posting it into the originating conversation. ``tier`` resolves through the registry. Never raises:
        any failure returns the raw ``deep_output`` unchanged.
        """
        try:
            model = self.registry.resolve_tier(tier)
            return self.synthesize_after_deep(
                request, prior_answer="", deep_output=deep_output,
                transcript=transcript, model=model, rep_preamble=rep_preamble,
                prompt_template=self.answer_kit.synthesize_task_report)
        except Exception:  # noqa: BLE001  a report rewrite must never break task reporting
            self.answer_kit.log.warning("task report synthesis failed; using raw output", exc_info=True)
            return deep_output

    def report_claims_unbacked(self, request: str, report_text: str,
                               exec_record: Optional[ExecutionRecord]) -> Optional[bool]:
        """PUBLIC: claim-check a synthesized report against the run's execution record.

        Returns True when the report claims completed work the execution record does NOT back (``claims_unexecuted``), False
        when the claims are clean, and None when the check could not run (no record, outage, parse failure). Callers must
        treat None as "do not trust the rewrite" and fall back to the verified raw output. Never raises.
        """
        if exec_record is None:
            return None
        try:
            verdict, _err = self.verify_goal(
                self.answer_kit.report_goal.format(request=request), request, report_text,
                exec_record=exec_record)
            if verdict is None:
                return None
            return bool(verdict.get("claims_unexecuted"))
        except Exception:  # noqa: BLE001  a claim check must never break task reporting
            self.answer_kit.log.warning("task report claim check failed", exc_info=True)
            return None

    def answer_subquestions(self, user_message: str, transcript: str, context_view: str,
                            gathered: List[Dict[str, Any]], model: str,
                            subquestions: List[str],
                            native_blocks: Optional[List[Dict[str, Any]]] = None,
                            reply_directive: Optional[str] = None,
                            rep_preamble: Optional[str] = None) -> str:
        kit = self.answer_kit
        subs = [s for s in subquestions if s][: self.cfg.max_subquestions]
        if len(subs) < 2:
            return self.grounded_answer(user_message, transcript, context_view, gathered, model,
                                        False, native_blocks=native_blocks,
                                        rep_preamble=rep_preamble,
                                        reply_directive=reply_directive)
        ground = kit.grounding_block(context_view, gathered, False)
        # Same contract as grounded_answer: a per-turn reply directive rides on the system prompt.
        sub_system = (f"{kit.reply_voice_system}\n\n{reply_directive}" if reply_directive
                      else kit.reply_voice_system)

        def answer_one(sub: str) -> Optional[Dict[str, str]]:
            try:
                # Each sub-question gets the native image blocks too, so any visual sub-question can see the image.
                focus = kit.subquestion_focus.format(sub=sub)
                if native_blocks:
                    focus_content: List[Dict[str, Any]] = list(native_blocks)
                    focus_content.append({"type": "text", "text": focus})
                    sub_msg = {"role": "user", "content": focus_content}
                else:
                    sub_msg = {"role": "user", "content": focus}
                # The per-turn preamble leads, exactly as on the single-answer path.
                msgs = [{"role": "user", "content": ground}, sub_msg]
                if rep_preamble:
                    msgs.insert(0, {"role": "user", "content": rep_preamble})
                provider = self.get_provider_for_model(model)
                # A single surviving sub-answer is returned verbatim (see below), so each one is written under the same
                # voice contract as a whole reply.
                return {"q": sub, "a": answer_with_reasoning(provider, msgs, model=model,
                                                             step=STEP_REPLY, system=sub_system)}
            except Exception as e:  # noqa: BLE001
                kit.log.warning(f"Sub-question answer generation failed: {type(e).__name__}: {e}", exc_info=True)
                return None

        workers = min(self.cfg.max_parallel, len(subs))
        out: List[Optional[Dict[str, str]]] = [None] * len(subs)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(answer_one, s): i for i, s in enumerate(subs)}
            for f in futs:
                try:
                    out[futs[f]] = f.result()
                except Exception as e:  # noqa: BLE001
                    kit.log.warning(f"Sub-question result collection failed: {type(e).__name__}: {e}", exc_info=True)
                    out[futs[f]] = None
        ok = [a for a in out if a and (a.get("a") or "").strip()]
        if not ok:
            return self.grounded_answer(user_message, transcript, context_view, gathered, model,
                                        False, native_blocks=native_blocks,
                                        rep_preamble=rep_preamble,
                                        reply_directive=reply_directive)
        if len(ok) == 1:
            return ok[0]["a"]
        merged = "\n\n".join(kit.merged_part.format(q=a["q"], a=a["a"]) for a in ok)
        try:
            merge_msgs: List[Dict[str, Any]] = (
                [{"role": "user", "content": rep_preamble}] if rep_preamble else [])
            return answer_with_reasoning(
                self.provider,
                merge_msgs + [{"role": "user", "content": kit.merge_prompt.format(message=user_message, merged=merged)}],
                model=model,
                step=STEP_REPLY,
                system=sub_system,     # the merge writes the reply too, so it obeys the directive
            )
        except Exception:  # noqa: BLE001
            return "\n\n".join(a["a"] for a in ok)
