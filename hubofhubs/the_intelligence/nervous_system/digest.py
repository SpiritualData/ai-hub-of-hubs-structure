"""The digest of one step: the short, bounded text a risk watch reads (the plan, its rationale, the spend and the history that matters). Standard
library only; it never raises."""
from typing import Any, List, Optional


def oneline(s: Any, limit: int = 160) -> str:
    text = " ".join(str(s or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def cap_section(text: str, cap: int) -> str:
    """Hard-cap one already-rendered, possibly-multi-line SHEDDABLE section to ``cap`` chars, so a
    single section (e.g. a long RECENT CONVERSATION) can never by itself crowd out the others.
    Never raises."""
    try:
        if len(text) <= cap:
            return text
        return text[: max(0, cap - 3)].rstrip() + "..."
    except Exception:  # noqa: BLE001
        return text


# Per-section caps for the SHEDDABLE "history" sections : each is bounded on its own, on top
# of the overall fit-to-budget pass below, so no single history section can dominate the digest.
RECENT_CONVERSATION_CHAR_CAP = 500
PRIOR_ESCALATIONS_CHAR_CAP = 300
OPERATIONS_CHAR_CAP = 700


def build_digest(
    *,
    user_message: str,
    goal_condition: Optional[str] = None,
    step: int,
    max_steps: int,
    plan_action: str = "",
    plan_rationale: str = "",
    plan_goal: str = "",
    recent_conversation: Optional[List[str]] = None,
    prior_escalations: Optional[List[str]] = None,
    operations: Optional[List[str]] = None,
    operations_total: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    elapsed_seconds: float = 0.0,
    max_elapsed_seconds: float = 0.0,
    gathered_chars: int = 0,
    max_gathered_chars: int = 0,
    consecutive_reads: int = 0,
    draft_answer: Optional[str] = None,
    quality_standards: Optional[str] = None,
    situation_standard: Optional[str] = None,
    draft_measurements: Optional[str] = None,
    draft_chars: int = 200,
    char_budget: int = 1600,
) -> str:
    """Build a compact, one-glance digest of the run for the overseer, capped at ``char_budget``.

    Pure and never-raising. ``user_message`` is the RAW, VERBATIM text the user typed; it is always
    shown so the overseer gets the same word-for-word fidelity the planner gets. ``goal_condition``
    is the RESOLVED, self-contained request (anaphora like "do it" rewritten into the concrete
    instruction); when it differs from ``user_message`` it is shown as an additional ``RESOLVED AS``
    line, never as a silent replacement.

    ``operations`` are already-tagged, one-lined summaries of the operations executed so far THIS
    RUN (e.g. "[read] cli.py -> found argparse subcommands...", produced by the caller so the FULL
    observation bodies never reach the overseer); ``operations_total`` is the true count so far
    (``operations`` may be a trailing window when the run is long). ``recent_conversation`` is a
    handful of PRIOR user turns in this SAME conversation (across turns, not this run); the caller is
    responsible for excluding the current turn's own request so it is never duplicated against
    CURRENT USER REQUEST. ``prior_escalations`` is a caller-supplied history of earlier turns in this
    conversation that already escalated (to deep execution or to a human) and their outcome.

    ``quality_standards``, when present, is the written completion/quality bar the result must clear.
    The ``AGENT'S READ BUDGET`` line reports the MAIN AGENT's own cumulative raw-read volume against
    its read cap, which is unrelated to this digest's own (tiny) size.

    ``situation_standard`` is the one-line standard written for a reviewer that applies to THIS reply's situation, and
    ``draft_measurements`` the deterministic counts and data comparisons the caller computed on the draft (both are the
    caller's data). They ride in the protected tail beside the draft, and ``draft_chars`` is how much of the draft is shown
    (a standard about the whole reply needs more than the default glance).

    TRUNCATION ORDER : the fields that actually drive a decision -- CURRENT USER REQUEST,
    RESOLVED AS, QUALITY BAR, PASS, CURRENT PLAN, RATIONALE, SPEND, TIME, AGENT'S READ BUDGET, and
    DRAFT ANSWER -- are PROTECTED: they are built first and always included in full. The "history"
    sections (RECENT CONVERSATION, PRIOR ESCALATIONS THIS CONVERSATION, OPERATIONS THIS TURN) are
    SHEDDABLE: each gets its own per-section cap, and if the overall ``char_budget`` is still tight,
    whole sheddable sections are dropped until it fits: operations first, then recent conversation, and
    PRIOR ESCALATIONS last, because a refusal recorded there must not be asked again. Only if the protected
    fields ALONE somehow exceed ``char_budget`` (a pathologically small budget) does a last-resort
    tail-truncation kick in, matching the previous behavior.
    """
    try:
        um = (user_message or "").strip()
        gc = (goal_condition or "").strip()

        # --- PROTECTED head: the user's own request, always first, always in full. -------------
        head: List[str] = [f"CURRENT USER REQUEST: {oneline(um, 300)}"]
        if gc and gc != um:
            head.append(f"RESOLVED AS: {oneline(gc, 300)}")
        if quality_standards:
            head.append(f"QUALITY BAR: {oneline(quality_standards, 200)}")

        # --- SHEDDABLE middle: cross-turn history. Each section individually capped, and this
        # whole block is what gets trimmed/dropped first if the overall budget is tight . ---
        sheddable: List[str] = []
        # Shedding priority, first dropped to last: operations, then recent conversation, then prior
        # escalations (a refusal there is what stops the same proposal being put to the user again).
        shed_rank: List[int] = []

        conv = [c for c in (recent_conversation or []) if c and str(c).strip()]
        if conv:
            n = len(conv)
            lines = [f"RECENT CONVERSATION (last {n} turn{'s' if n != 1 else ''}):"]
            lines.extend(f"  - {oneline(c, 160)}" for c in conv)
            sheddable.append(cap_section("\n".join(lines), RECENT_CONVERSATION_CHAR_CAP))
            shed_rank.append(1)

        esc = [e for e in (prior_escalations or []) if e and str(e).strip()]
        if esc:
            lines = ["PRIOR ESCALATIONS THIS CONVERSATION:"]
            lines.extend(f"  {oneline(e, 160)}" for e in esc)
            sheddable.append(cap_section("\n".join(lines), PRIOR_ESCALATIONS_CHAR_CAP))
            shed_rank.append(2)
        else:
            sheddable.append("PRIOR ESCALATIONS THIS CONVERSATION: none yet")
            shed_rank.append(0)

        ops = [o for o in (operations or []) if o and str(o).strip()]
        if ops:
            total = operations_total if operations_total else len(ops)
            start_num = max(1, total - len(ops) + 1)
            lines = [f"OPERATIONS THIS TURN ({total} so far):"]
            lines.extend(f"  {start_num + i}. {oneline(o, 160)}" for i, o in enumerate(ops))
            sheddable.append(cap_section("\n".join(lines), OPERATIONS_CHAR_CAP))
        else:
            sheddable.append("OPERATIONS THIS TURN: none yet")
        shed_rank.append(0)

        # --- PROTECTED tail: the fields the decision actually turns on. Always included in full. -
        tail: List[str] = [f"PASS: {step} of {max_steps}"]
        plan_bits: List[str] = []
        if plan_action:
            plan_bits.append(f"action={plan_action}")
        if plan_goal:
            plan_bits.append(f"goal={oneline(str(plan_goal).splitlines()[0] if plan_goal else '', 120)}")
        if plan_bits:
            tail.append("CURRENT PLAN: " + ", ".join(plan_bits))
        if plan_rationale:
            tail.append(f"RATIONALE: {oneline(plan_rationale, 200)}")
        tail.append(
            f"SPEND: tokens_in={tokens_in} tokens_out={tokens_out}; "
            f"consecutive_reads={consecutive_reads}"
        )
        if max_elapsed_seconds:
            tail.append(f"TIME: {elapsed_seconds:.0f}s of {max_elapsed_seconds:.0f}s budget")
        if max_gathered_chars:
            tail.append(
                f"AGENT'S READ BUDGET: {gathered_chars} of {max_gathered_chars} chars gathered "
                f"so far (the agent's own cumulative reads, NOT this digest's size)"
            )
        if draft_answer:
            shown = max(200, int(draft_chars or 200))
            tail.append(f"DRAFT ANSWER (first {shown} chars): {oneline(draft_answer, shown)}")
            if situation_standard:
                tail.append(f"SITUATION STANDARD: {oneline(situation_standard, 400)}")
            if draft_measurements:
                tail.append(f"DRAFT MEASUREMENTS: {oneline(draft_measurements, 500)}")

        budget = max(1, int(char_budget))
        full_text = "\n".join(head + sheddable + tail)
        if len(full_text) <= budget:
            return full_text

        # Over budget: drop whole SHEDDABLE sections (operations, then conversation, then escalations) until it fits. head/tail
        # are NEVER touched here (the must-survive guarantee).
        shed = list(range(len(sheddable)))
        for idx in sorted(shed, key=lambda i: (shed_rank[i], -i)):
            if len("\n".join(head + [sheddable[i] for i in shed] + tail)) <= budget:
                break
            shed.remove(idx)
        shed = [sheddable[i] for i in shed]
        fitted = "\n".join(head + shed + tail)
        if len(fitted) <= budget:
            return fitted

        # Last resort: even head+tail alone exceed budget (a pathologically small char_budget).
        # Fall back to a hard tail-truncation so the function still returns something bounded.
        return fitted[: max(0, budget - 3)].rstrip() + "..."
    except Exception:  # noqa: BLE001 a digest hiccup must never break the run
        return oneline(user_message, min(300, max(1, char_budget)))
