"""The lines that show what is unique to the hub, in plain words: the ceilings against the spend and the time, the soft limit, the hub's own stop or continue, and the
end of a run (what is left and the command that resumes it). All are small pure functions of the values a ``SessionView`` keeps; none is shown unless there is something
to say, and the detail behind them is opened only on request. Standard library only."""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Tuple

REASONS = {
    "no_code_finding": "the check found nothing left to fix",
    "resume_limit": "it already went round once more and that is the most it does by itself",
    "resume_cap": "it reached the most rounds it may start by itself",
    "ceiling_spend": "the spend ceiling is nearly used",
    "ceiling_time": "the time ceiling is nearly used",
    "ceiling_turns": "the turn ceiling is reached",
    "code_finding": "the check found something to fix",
    "cancelled": "you stopped the run",
    "declined": "nothing asked for another round",
    "stop_met": "the goal is met",
    "stop_good_enough": "what is done is good enough for the goal",
    "stop_not_worth_it": "another round would cost more than it is likely to gain",
    "ask": "only you can say what is missing",
    "plateau": "the last round gained almost nothing",
    "oscillation": "the rounds undo each other",
    "regress": "the last round made it worse",
}
CEILING_WORDS = {"spend": "spend", "time": "time"}


def reason_words(code: str) -> str:
    code = (code or "").strip()
    if code.startswith("decision_failed"):
        return "the decision could not be made, so no further round was started"
    return REASONS.get(code, code.replace("_", " ")) if code else "no reason was given"


def clock(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    hours, rest = divmod(seconds, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def dollars(value: float) -> str:
    return f"${value:.2f}" if value >= 1 else f"${value:.4f}"


def status_segment(elapsed: float, cost: Optional[float], ceiling_usd: Optional[float], ceiling_seconds: Optional[float]) -> Tuple[str, str]:
    """The quiet spend and time segments: ``("0:42 of 4:00:00", "$0.0123 of $20.00")``. With no ceiling the figure stands alone."""
    when = f"{clock(elapsed)} of {clock(ceiling_seconds)}" if ceiling_seconds else clock(elapsed)
    if cost is None:
        spent = "cost unknown"
    else:
        spent = f"{dollars(cost)} of {dollars(ceiling_usd)}" if ceiling_usd else dollars(cost)
    return when, spent


def nearest_ceiling(elapsed: float, cost: Optional[float], ceiling_usd: Optional[float], ceiling_seconds: Optional[float]) -> Tuple[float, str]:
    """``(share used, "spend" or "time")`` of the ceiling the run is closest to; ``(0.0, "")`` with no ceiling."""
    shares = []
    if ceiling_seconds:
        shares.append((elapsed / ceiling_seconds, "time"))
    if ceiling_usd and cost is not None:
        shares.append((cost / ceiling_usd, "spend"))
    return max(shares, default=(0.0, ""))


def soft_limit_line(elapsed: float, cost: Optional[float], ceiling_usd: Optional[float], ceiling_seconds: Optional[float]) -> str:
    """One line: the run is wrapping up, and why."""
    share, what = nearest_ceiling(elapsed, cost, ceiling_usd, ceiling_seconds)
    if not what:
        return "Wrapping up: it reached the soft limit of its ceiling and is finishing at a safe stopping point"
    when, spent = status_segment(elapsed, cost, ceiling_usd, ceiling_seconds)
    used = when if what == "time" else spent
    return f"Wrapping up: {int(share * 100)} percent of the {CEILING_WORDS[what]} ceiling is used ({used}); finishing at a safe stopping point, then you can resume or raise it"


def hard_limit_line(what: str) -> str:
    return f"Stopped at the {CEILING_WORDS.get(what, what or 'ceiling')} limit: finished work is kept and the session can be resumed"


def stopping_line() -> str:
    """The one line shown at the moment a stop was asked for (the closing says the rest once the run has ended)."""
    return "Stopping: finished work is kept, and the session can be resumed"


def decision_line(decision: str, reason: str) -> str:
    return f"Hub decision: {'go on' if decision == 'continue' else 'stop'}, {reason_words(reason)}"


def left_line(outcome: str, error: str, end_reason: str, unseen: int) -> str:
    """What is left, in one sentence, from how the run ended; empty when the run met its goal with nothing waiting."""
    parts = []
    if outcome == "stopped":
        pass            # the closing's stop lines say it (``present.stop_lines``)
    elif outcome in ("unmet", "failed"):
        parts.append("the goal is not yet met")
    if end_reason.startswith("resume_stopped:"):
        parts.append("the hub chose not to go round again because " + reason_words(end_reason.split(":", 1)[1]))
    elif end_reason.startswith("stopped_at_hard_limit"):
        pass            # said once by the closing's stop lines
    elif end_reason == "wrapped_up_at_soft_limit":
        parts.append("it wrapped up at the soft limit of its ceiling, so some work may be unfinished")
    if error and outcome not in ("met", "stopped") and not end_reason.startswith("stopped_at_hard_limit"):
        parts.append(error.strip().rstrip("."))
    if unseen:
        parts.append(f"{unseen} message{'' if unseen == 1 else 's'} you sent {'was' if unseen == 1 else 'were'} not taken up (sent again on resume)")
    return "; ".join(parts)


def stop_limit_words(limits: Optional[Mapping[str, Any]]) -> str:
    """The stated stop limits and the policy bounds of ``representatives.stop_limits.resolve_stop_limits``, as one phrase; empty when none."""
    stated, policy = (limits or {}).get("stated") or {}, (limits or {}).get("policy") or {}
    bits = []
    if stated.get("stop"):
        bits.append("stop when asked")
    if stated.get("one_pass"):
        bits.append("one pass only")
    if stated.get("max_iterations") is not None:
        bits.append(f"at most {stated['max_iterations']} rounds")
    if stated.get("keep_going_until"):
        bits.append(f"keep going until {stated['keep_going_until']}")
    if stated.get("until_reached"):
        bits.append("keep going until the milestone is reached")
    if policy.get("max_iterations") is not None:
        bits.append(f"policy caps rounds at {policy['max_iterations']}")
    if policy.get("forbids_iteration"):
        bits.append("policy forbids going round again")
    if policy.get("authority_exhausted"):
        bits.append("the authority for more rounds is used up")
    return "; ".join(bits)


def authority_lines(representative: Optional[Mapping[str, Any]], limits: Optional[Mapping[str, Any]] = None) -> List[str]:
    """What the Representative in force lets the AI do, one line each: the worker categories allowed, the data scope, the asking policy and the stated stop limits.
    Empty with no representative."""
    if not representative or not representative.get("person"):
        return []
    authority = representative.get("authority") or {}
    ask = authority.get("ask") or {}
    asking = ", ".join(f"{key}: {value}" for key, value in ask.items()) if isinstance(ask, Mapping) and ask else "none declared, so the hub's default"
    lines = [f"Acting for: {representative['person']}",
             "  Worker categories allowed: " + (", ".join(str(x) for x in authority.get("allow") or ()) or "none"),
             "  Data scope: " + (", ".join(str(x) for x in authority.get("data_scope") or ()) or "none"),
             f"  Asking policy: {asking}"]
    words = stop_limit_words(limits)
    lines.append("  Stop limits: " + (words or "none stated"))
    return lines


def resume_command(session_id: str, command: str = "ahohs work") -> str:
    """The command that continues the session, to be run in the same folder: the id only, because the harness that ran it is recorded with it (``session_memory``)."""
    return f"{command} --resume {session_id}"


__all__ = ["REASONS", "clock", "decision_line", "dollars", "hard_limit_line", "authority_lines", "left_line", "nearest_ceiling", "stop_limit_words", "reason_words", "resume_command", "soft_limit_line", "status_segment"]
