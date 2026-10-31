"""The planner's structured next-step decision: one iteration of the loop.

A plain value object. The labels it carries (the deep target, the model tier, the work shape) are the consumer's vocabulary;
the loop only compares them with what the consumer passed in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanDecision:
    """The planner's structured next-step decision (one iteration of the loop)."""
    action: str                                   # "read" | "answer" | "deep" | "confirm" | "clarify" | "tool"
    reads: List[Dict[str, Any]] = field(default_factory=list)
    goal: Optional[str] = None
    deep_brief: Optional[str] = None
    confirm_question: Optional[str] = None
    model_tier: Optional[str] = None              # a tier name the consumer defines | None
    # The planner's rating of DEEP work, judged on the same planning call (zero extra LLM calls):
    # "simple" | "normal" | "hard" | None. Picks the deep run's STARTING model when nothing pinned
    # one. None = not assessed; the ladder is then unchanged.
    deep_difficulty: Optional[str] = None
    deep_difficulty_reason: Optional[str] = None  # one short clause, logged with the choice
    # WHAT a "deep" (or deferred_deep) change lands on, judged on the same planning call (zero
    # extra LLM calls): "records" | "code_or_files" | "other" | None (the labels are the consumer's). A
    # "records" target gates the deep-runner ladder so a change to records never lands on a file-editing rung. None = not assessed; the ladder is unchanged.
    deep_target: Optional[str] = None
    subquestions: List[str] = field(default_factory=list)
    # Flat task dicts; with staged plans on, also lists (sequences) of dicts or of
    # lists of dicts. See staged_plan.
    deep_subtasks: List[Any] = field(default_factory=list)
    rationale: str = ""
    # Optional deferred deep work: when action="answer", can also queue a deep task to run after
    deferred_deep: Optional[Dict[str, Any]] = None  # {"goal": "...", "brief": "...", "rationale": "..."}
    # Explicit signal: this answer contains work that needs execution (instead of regex guessing)
    answer_contains_work_to_execute: bool = False  # Set True if answer describes work the AI should do
    # The planner chose "answer" for a message that asks it to ACT because what it read shows the act
    # cannot or should not go ahead as asked (a stored constraint, a conflict); the reply says so and
    # gives the nearest option that works. That reply IS the complete response, so the escalation nets
    # that turn an answer to an "act" message into a deep run must not fire on it.
    act_declined: bool = False
    # The planner chose "answer" for a message that cannot be acted on or planned without facts only the person holds (their times,
    # their choices): the reply asks for them first and drafts nothing. A structured self-report on the planning call, so the reply
    # writer is told by a field, never by the wording of the planner's prose.
    asks_first: bool = False
    # User clarification/input needed: when action="clarify"
    clarification: Optional[Dict[str, Any]] = None  # {"question": "...", "options": [...], "allow_free_input": bool}
    # EXPLICIT execution-mode signal the planner detected in the user's message (LLM judgment on
    # the planning call it already makes; never phrase matching). "enter_brainstorm" |
    # "exit_brainstorm" | None. Anything else the model returns is normalized to None (fail-safe:
    # a detection failure never changes the mode).
    mode_signal: Optional[str] = None
    # PER-IDEA THREADING (opt-in): which TOPIC CARD this
    # message belongs to, judged on the SAME planning call (zero extra LLM calls). Raw field, exactly one of "continue" | "switch_to:<card_id>" |
    # "new:<label>"; anything else is normalized to None and the turn CONTINUES the active card
    # (the standing fail-safe: an ambiguous topic assignment must never cost a turn). A topic
    # switch is NOT a mode signal and never touches the brainstorm latch.
    card_thread: Optional[str] = None
    # The escalation this confirm/clarify raises, all optional and all defaulting to the same
    # behavior as before they existed: a decision KIND (a short label such as "approve" or
    # "explicit:spend", validated and defaulted again at the consumer's boundary, so a hallucinated value here
    # degrades rather than losing the escalation); a deadline the decision should be resolved by, as the planner
    # wrote it (an ISO datetime, or a short relative form like "in 48h", parsed by the consumer; unparseable or
    # absent means no deadline); and
    # "hold" | "proceed" for what happens if nobody answers by the deadline ("proceed" auto-
    # resolves the decision server-side; anything else, including no deadline at all, "hold"s).
    confirm_kind: Optional[str] = None
    confirm_deadline: Optional[str] = None
    # OPTIONAL http(s) link to the thing the human should look at to answer (the escalation's review link).
    confirm_review_url: Optional[str] = None
    confirm_default_on_silence: Optional[str] = None
    # action="tool": the direct tool calls to run in-process, in order, each
    # ``{"name": "<tool>", "args": {...}}`` Only ever populated when the
    # loop was given a tool registry; otherwise "tool" is not an action the planner has.
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    # HOW SURE the planner is of THIS decision, judged on the same planning call (zero extra LLM
    # calls): "high" | "medium" | "low" | None. Present only when the consumer opted into the
    # cascade (the planner cascade), because a field nobody reads is input tokens
    # on every call for nothing. It is a STRUCTURED self-report the planner fills in, which is why
    # it is an acceptable escalation signal where scanning the planner's own prose would not be
    # (a self-report, never a reading of prose). None = not assessed, and the cascade then leaves the decision
    # alone rather than escalating everything.
    confidence: Optional[str] = None
    # WHAT THE USER'S CURRENT MESSAGE ASKS OF THE ASSISTANT, judged on the same planning call (zero
    # extra LLM calls): "act" (do, produce or change something now) | "ask" (a question, or asking
    # to be told something) | "inform" (news, context, or the user's own plan) | "hold_off" (do
    # not open work, answer here, stop or cancel runs). The loop's escalation nets honor
    # this structured verdict instead of reading the message with a keyword list. None = not given
    # (the nets then fall back to the one-shot intent judge, never to a regex).
    user_intent: Optional[str] = None
    # THE READS THIS DECISION STILL OWES, declared by the planner on the call it already makes (zero
    # extra LLM calls): read specs (same shape as ``reads``) for sources it has located but not
    # opened, which the answer it is giving depends on. Empty = the answer is complete. When an
    # ``answer`` decision carries any, the loop runs them first instead of answering (the planner's
    # own structured declaration, never a reading of its prose).
    pending_read: List[Dict[str, Any]] = field(default_factory=list)
    # THE FACTS THIS DECISION RESTS ON, declared by the planner on the call it already makes (zero extra
    # LLM calls): each fact in CONTEXT and GATHERED that bears on the request, as a short quote with its
    # source. The planner is the one reader that sees the newest reads in full beside the request, so what it
    # lists is carried on: appended to a deep brief (a change must respect a stored constraint the code
    # writer never read) and shown to the answer (which reads every gathered page of a long turn).
    facts_read: List[str] = field(default_factory=list)
    # WHAT KIND OF WORK this request is, judged on the planning call that already happens (zero extra calls;
    # opt-in): "lookup" | "action" | "analysis" | "conversation" | None.
    # The planner's own structured judgement, never a reading of any text. Only "analysis" (a question over a
    # whole set, or one that needs a method) turns anything else on: the plan-sufficiency pre-flight and the
    # done-evidence the verifier checks. None = not given, and the turn runs exactly as it did before.
    work_shape: Optional[str] = None
    # THE CHECKABLE EVIDENCE that would show the work is done, declared by the planner for an "analysis" only: up to
    # four short requirements (coverage of the named set, a method that fits the question, gaps and limits stated).
    # Written BEFORE the work so the plan is made backwards from them; the verifier judges each one, reading
    # coverage from the run's structured ``DeepResult.coverage`` and not from its prose.
    done_evidence: List[str] = field(default_factory=list)
