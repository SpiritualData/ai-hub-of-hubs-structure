"""The loop's default bounds and the two structural checks on a deep result.

Every number is a default the consumer's configuration can override. The two predicates judge a deep result on its structured
fields only, never on what its wording says.
"""
from __future__ import annotations

from typing import Any

# Defaults. The elapsed/chars budget bounds the WHOLE read cascade for a turn (every grep and read this turn shares it), not a
# single read: a tight cap left a simple "check these 3 named files" request no room after one broad grep, so the turn gave
# up mid-cascade and reported a false "could not check X". Widened so a normal few-file lookup completes within budget.
DEFAULT_MAX_STEPS = 15
DEFAULT_MAX_ELAPSED_SECONDS = 90.0
DEFAULT_MAX_GATHERED_CHARS = 150000
DEFAULT_MAX_READS_PER_STEP = 8
DEFAULT_MAX_PARALLEL = 8
DEFAULT_MAX_SUBQUESTIONS = 4
DEFAULT_MAX_DEEP_SUBTASKS = 4
# A staged plan: at most this many steps in one sequence and this many tasks across the plan. The top level keeps the
# DEFAULT_MAX_DEEP_SUBTASKS cap a flat list has always had.
DEFAULT_MAX_PLAN_STAGES = 4
DEFAULT_MAX_PLAN_TASKS = 8
DEFAULT_DEEP_MAX_TURNS = 30

# How far a CONTINUATION may grow one attempt's turn budget. Each continuation gets ``deep_max_turns * (n + 1)`` turns,
# capped here: a task that needed a bit more room gets it quickly, while a worker that is genuinely going in circles cannot
# talk its way into an unbounded run one continuation at a time.
DEEP_CONTINUATION_TURN_MULTIPLIER_CAP = 4

# AUTOMATIC FOLLOW-UP RUNS. When a task's deep run ends with the original ask clearly unfinished (the verifier or the worker
# named what remains) and nothing is waiting on a person, the executor starts another deep run for the remaining items
# instead of ending the task with "what is left" text. Bounded two ways: this many follow-up runs per task execution (0
# turns the behaviour off), and a token budget over the whole chain: the per-run goal-loop budget (300k by default) for the
# first run plus one more for each follow-up, so the chain can never cost more than its cap allows.
AUTO_FOLLOWUP_MAX_RUNS = 3
AUTO_FOLLOWUP_TOKEN_BUDGET = 300_000 * (1 + AUTO_FOLLOWUP_MAX_RUNS)
# How much of the original ask and of the previous run's report a follow-up brief carries.
AUTO_FOLLOWUP_ASK_MAX_CHARS = 3000
AUTO_FOLLOWUP_DONE_MAX_CHARS = 3000
AUTO_FOLLOWUP_REMAINING_MAX_CHARS = 1500

DEFAULT_MAX_GATHER_CHARS = 6000
DEFAULT_MAX_CONSECUTIVE_READS = 20

# How many times one turn may swap an `answer` for the reads the planner itself declared it still owes. Bounded so a planner
# that keeps declaring a read it never gets value from still ends in an answer.
PENDING_READ_MAX_RUNS = 2

# Lean re-plan view: the planner is re-fed the WHOLE cumulative ``gathered`` each step, which bloats fast on multi-read runs.
# Instead, keep the most-recent observations in full and COMPRESS older ones to one-line summaries, but only once
# ``gathered`` has grown past a threshold, so short runs are unchanged. The full ``gathered`` is still used verbatim for the
# final ANSWER synthesis; only the per-step PLANNER view is leaned out.
DEFAULT_PLANNER_RECENT_FULL = 4      # newest N observations rendered in full to the planner

# Hard character caps on the three volatile sections of the planner prompt (0 disables a cap). The planner only routes, so it
# needs the latest turns and the head of the context, not all of it; the final ANSWER path keeps the full transcript and
# context.
DEFAULT_PLANNER_TRANSCRIPT_MAX_CHARS = 8_000
DEFAULT_PLANNER_CONTEXT_MAX_CHARS = 8_000
DEFAULT_PLANNER_GATHERED_MAX_CHARS = 10_000
DEFAULT_PLANNER_COMPRESS_OVER = 6    # leave gathered untouched until it exceeds this many obs

# Cross-step repeat-context leaning: within a SINGLE run the transcript and the static context view never change between
# steps, yet re-planning re-sent BOTH in full on every step. On re-plan steps the planner's job is to REACT to the new
# ``gathered`` observations, not to re-read context it already saw on step 1. When enabled, steps after the first replace the
# unchanged transcript and context view with a short "already provided on step 1" reference. This never affects step 1 and
# never affects the final ANSWER (which always gets the full transcript and context view).
#
# Default ON (2026-10-06, token-usage pass): the static context view alone measured about 5,200 tokens on a real planner
# call, and with about 2.4 planner calls per turn, re-sending that unchanged block on every re-plan step was most of the cost
# for no benefit the planner could use. Flip back to False only if a planner genuinely needs the raw context on a re-plan
# step; the final answer is unaffected either way.
DEFAULT_PLANNER_ABBREVIATE_REPEAT_CONTEXT = True

# CARD MERGE (semantic dedup). When the post-deep card updater would CREATE a NEW card, it first asks the vector-backed card
# store whether a sufficiently-similar card already exists for THIS user (by embedding COSINE similarity) and, if so, UPDATES
# that card instead of creating a near-duplicate twin. This default is the COSINE floor a candidate must clear to count as
# the "same" card: HIGH on purpose, so only a CLEAR twin merges and an unrelated card is never collapsed. A value of 1.0
# effectively DISABLES the behavior (cosine almost never reaches a clean 1.0 except an identical card), as does a card store
# with no embeddings.
DEFAULT_CARD_MERGE_SIMILARITY = 0.85


def result_reports_something(result: Any) -> bool:
    """Whether a deep result has anything of its own to tell the person: text it produced, a verified outcome, or a
    usage-limit wait.

    Used where a fan-out's results are trimmed around a single ask: a sibling subgoal that was stopped before it ever ran
    leaves an EMPTY placeholder result, which must not become a blank paragraph in the reply, while a sibling that genuinely
    finished its work must survive. Judged on structure and emptiness only, never on what any wording says. Never raises."""
    try:
        if (getattr(result, "output", "") or "").strip():
            return True
        return bool(getattr(result, "met", False) or getattr(result, "usage_limited", False))
    except Exception:  # noqa: BLE001
        return False


def result_landed_work(result: Any) -> bool:
    """Whether a deep result is work that really LANDED, judged only on its structured fields.

    The run's OWN RECORDS decide: not parked on a decision (``decision_id``); its write receipts do not say it changed nothing
    (``changed_nothing``); and, when the runner records what it observed (``observations_reported``), a run that was NOT
    verified met either observed something, or is the runner's own TERMINAL ASK for this turn (``exhausted``, see below).
    "Not parked" alone is NOT "landed": a sibling that failed, or could not be verified and has no receipt of any effect,
    folded into a "you already did the work" synthesis is how a failure was reported as done. A verified text answer with
    nothing to record still counts (its answer is the work), and a runner that keeps no receipts at all
    (``observations_reported`` False) is judged as before: this is deliberately narrower than "exhausted and not met" alone
    would be, because the loop's OWN goal loop also sets ``exhausted`` on a result whose verification merely could not run
    (no receipts ever reported), and that is genuinely finished work.

    ``observations_reported`` and ``exhausted`` TOGETHER: a receipt-tracking runner can end a turn with its own honest
    terminal message (a clarifying question, "I could not reliably turn that into a change", a spent code-generation budget)
    WITHOUT a ``decision_id`` (that field is only for an approval-card park). Such a result may still carry real, non-empty
    ``observations`` (a reconnaissance read genuinely found data before the runner gave up on WHICH record to write it to), so
    the plain "observed nothing" check does not catch it. Live trace: a pace was computed correctly, the write's target was
    ambiguous, the runner asked which one was meant (met=False, exhausted=True, real observations), and folding that into the
    "you already DID the work" synthesis claimed something was queued when nothing was queued, parked, or written anywhere.

    ``has_write_receipt`` is the one exception to "exhausted and not met means not landed": a runner can end a turn
    ``exhausted`` and not ``met`` while a GENUINE PARTIAL WRITE already landed (three of five updates completed, then the
    fourth raised and the runner stopped rather than risk a duplicate retry). Dropping that receipt reported real work as not
    done. The flag is read, never the wording of ``observations`` or ``output``; a runner that cannot tell leaves it False.

    Structural throughout: driven by ``observations_reported``/``exhausted``/``met``/``has_write_receipt``, never by scanning
    the output text for "queued"/"asking"/"wrote". Never raises."""
    try:
        if getattr(result, "decision_id", None) or getattr(result, "changed_nothing", False):
            return False
        if getattr(result, "observations_reported", False) and not getattr(result, "met", False):
            if not (getattr(result, "observations", None) or []):
                return False
            if getattr(result, "exhausted", False) and not getattr(result, "has_write_receipt", False):
                return False
        return True
    except Exception:  # noqa: BLE001
        return False
