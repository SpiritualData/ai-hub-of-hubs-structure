"""The free gate that decides whether a step looks risky enough to wake an expensive overseer model."""
from __future__ import annotations


def worth_a_look(*, consecutive_reads: int, plan_repeats_prev: bool,
                 elapsed_seconds: float, max_elapsed_seconds: float,
                 gathered_chars: int, max_gathered_chars: int,
                 min_consecutive_reads: int, gate_repeat_plan: bool,
                 spend_fraction: float) -> bool:
    """FREE, non-model heuristic gate: whether the current step looks risky enough to be worth waking the expensive overseer
    model at all, instead of consulting on a blind fixed cadence regardless of how the run is actually going. True when ANY
    cheap signal suggests drift, looping, or budget pressure:
      - ``consecutive_reads`` has crossed ``min_consecutive_reads`` (a stuck read loop), or
      - the plan repeats the previous step's action and goal verbatim (``plan_repeats_prev``, when
        ``gate_repeat_plan`` is enabled: looping on the same idea), or
      - elapsed time OR gathered-read volume has crossed ``spend_fraction`` of its budget.
    Pure, never raises (a bad input just fails every check, so False, so the consult is skipped, which is safe)."""
    try:
        if consecutive_reads >= max(1, int(min_consecutive_reads)):
            return True
        if gate_repeat_plan and plan_repeats_prev:
            return True
        if max_elapsed_seconds and (elapsed_seconds / max_elapsed_seconds) >= spend_fraction:
            return True
        if max_gathered_chars and (gathered_chars / max_gathered_chars) >= spend_fraction:
            return True
        return False
    except Exception:  # noqa: BLE001
        return False
