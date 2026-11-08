"""Which arm of Delegated Agent Sessions a consumer gets, among the arms it can run.

An arm is ``<harness>@provider=<provider>,tier=<tier>`` (an esoi variant name, the same string as the ``impl`` of a results row). A
consumer declares the providers it holds credentials for; an arm is eligible when its provider is one of them and its harness can drive
that provider (``PROVIDERS`` on the harness class, see ``providers``). The choice, in order:

1. **measured**: the esoi cascade rule (``esoi.optimization.leaderboard.stage_standings.decide``) applied to the eligible arms only: the best
   result at the latest stage any of them reached, unless another eligible arm beat it at an earlier shared stage and has not been run
   at the latest one. The results come from the snapshot ``arm_standings.json`` beside this file, written from the results log by
   ``write_snapshot`` so an installed copy needs no records (``python3 -m hubofhubs.the_world.tools.delegated_agent_sessions.arm_choice``).
2. **public prior**: with no measured eligible arm, the eligible arm with the highest prior in ``public_priors.csv`` whose evidence grades
   C or better, labelled with its grade.
3. **idea**: else the eligible arm with the highest idea-stage rating in ``arm_ideas.csv`` (the scale is ``esoi/idea-rating-scale.md``).

The reason says which of these decided, so a consumer can log it. Nothing here reads the environment or calls a model.
"""
from __future__ import annotations

import csv
import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from hubofhubs.the_world.tools.delegated_agent_sessions import providers

SOLUTION = "delegated-agent-sessions"
METRIC = "metric-delegated-agent-sessions"
COMPONENT = "agent_sessions"
HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "arm_standings.json"
PRIORS = HERE / "public_priors.csv"
IDEAS = HERE / "arm_ideas.csv"
USABLE_GRADES = ("A", "B", "C")
IDEA_QUESTIONS = ("problem_fit", "purpose_fit", "real_conditions", "cost_and_risk", "checkability")


@dataclass
class ArmChoice:
    """The arm a consumer gets and why."""
    arm: str
    harness: str
    provider: str
    tier: str
    basis: str            # "measured", "public prior" or "idea"
    stage: str = ""       # the cascade stage the choice rests on (measured only)
    score: float = 0.0    # the balanced score, the prior or the idea rating the choice rests on
    reason: str = ""


def split_arm(arm: str) -> Tuple[str, str, str]:
    """``(harness, provider, tier)`` of an arm name; provider and tier are empty for a bare harness name."""
    from esoi.runtime.implementation_selection import variants
    base, params = variants.split(arm)
    return base, providers.normalise(str(params.get("provider", ""))), str(params.get("tier", ""))


def harness_class(harness: str) -> Any:
    """The declared implementation class of a harness name, or None when the hub declares none of that name."""
    from esoi import selection
    try:
        return selection.resolve(SOLUTION, harness, scope="hubofhubs")
    except (ValueError, ImportError):
        return None


def eligible(arm: str, declared: Iterable[str]) -> bool:
    """Whether a consumer that holds credentials for ``declared`` providers can run ``arm``."""
    harness, provider, tier = split_arm(arm)
    if not provider or provider not in providers.normalise_all(declared):
        return False
    cls = harness_class(harness)
    return cls is not None and providers.drives(cls, provider)


def read_snapshot(path: Path = SNAPSHOT) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read_rows(path: Path) -> List[Dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def number(text: Any) -> Optional[float]:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def measured_choice(declared: Iterable[str], snapshot: Dict[str, Any]) -> Optional[ArmChoice]:
    from esoi.optimization.leaderboard import cascade_stages, ranking
    from esoi.optimization.leaderboard.stage_standings import Standing, decide
    stages, problems = cascade_stages.parse(snapshot.get("cascade", ""))
    if not stages or problems:
        return None
    standing = {arm: Standing(arm, rows={int(i): row for i, row in by_stage.items()})
                for arm, by_stage in (snapshot.get("rows") or {}).items() if eligible(arm, declared)}
    decision = decide(stages, {a: s for a, s in standing.items() if s.rows})
    if not decision.winner:
        return None
    row = standing[decision.winner].rows.get(decision.stage) or max(standing[decision.winner].rows.items())[1]
    harness, provider, tier = split_arm(decision.winner)
    stage = stages[decision.stage].name if 0 <= decision.stage < len(stages) else ""
    passed = f"{row.get('passed', '?')}/{row.get('cases', '?')}"
    held = f"; held in place: {', '.join(decision.pending)}" if decision.pending else ""
    return ArmChoice(decision.winner, harness, provider, tier, "measured", stage, number(row.get("balanced")) or 0.0,
                     f"best eligible arm at the {stage} stage ({passed} passed, balanced {row.get('balanced', '?')}, "
                     f"pass rate {ranking.pass_rate(row):.2f}){held}")


def prior_choice(declared: Iterable[str], rows: List[Dict[str, str]]) -> Optional[ArmChoice]:
    usable = [r for r in rows if (r.get("grade") or "").strip().upper()[:1] in USABLE_GRADES and number(r.get("prior")) is not None
              and eligible(r.get("arm_id", ""), declared)]
    if not usable:
        return None
    best = max(usable, key=lambda r: number(r["prior"]))
    harness, provider, tier = split_arm(best["arm_id"])
    return ArmChoice(best["arm_id"], harness, provider, tier, "public prior", "public", number(best["prior"]) or 0.0,
                     f"no eligible arm is measured; best public prior {best['prior']} (grade {best['grade']}): {best.get('reason', '')}".strip())


def idea_rating(row: Dict[str, str]) -> Optional[float]:
    """The idea stage's number: the five ratings (0 to 4) summed over 20, or None when one is missing."""
    ratings = [number(row.get(q)) for q in IDEA_QUESTIONS]
    return None if any(r is None for r in ratings) else sum(ratings) / (4 * len(ratings))


def idea_choice(declared: Iterable[str], rows: List[Dict[str, str]]) -> Optional[ArmChoice]:
    rated = [(idea_rating(r), r) for r in rows if eligible(r.get("arm", ""), declared)]
    rated = [(score, r) for score, r in rated if score is not None]
    if not rated:
        return None
    score, best = max(rated, key=lambda pair: pair[0])
    harness, provider, tier = split_arm(best["arm"])
    return ArmChoice(best["arm"], harness, provider, tier, "idea", "idea", score,
                     f"no eligible arm is measured or has a usable public prior; best idea rating {score:.2f} (not measured)")


def choose_agent_arm(declared: Iterable[str], *, snapshot: Optional[Dict[str, Any]] = None, priors: Optional[List[Dict[str, str]]] = None,
           ideas: Optional[List[Dict[str, str]]] = None) -> Optional[ArmChoice]:
    """The arm for a consumer holding credentials for ``declared`` providers, or None when it can run no arm."""
    declared = providers.normalise_all(declared)
    return (measured_choice(declared, read_snapshot() if snapshot is None else snapshot)
            or prior_choice(declared, read_rows(PRIORS) if priors is None else priors)
            or idea_choice(declared, read_rows(IDEAS) if ideas is None else ideas))


def build_agent_runner(choice: ArmChoice, config: Any, **arguments: Any) -> Any:
    """An instance of the chosen arm: its harness class built from ``config`` with the arm's provider and tier (and any other
    constructor ``arguments`` the consumer passes, such as ``settings``)."""
    cls = harness_class(choice.harness)
    if cls is None:
        raise ValueError(f"the hub declares no harness {choice.harness!r}")
    return cls(config, provider=choice.provider, tier=choice.tier, **arguments)


def write_snapshot(root: Optional[Path] = None, path: Path = SNAPSHOT, today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """Write the counting result of every arm at each cascade stage, from the results log of the records tree at ``root``.
    Stale and expired results are left out, as the cascade rule leaves them out."""
    from esoi.optimization.leaderboard import cascade_stages
    from esoi.optimization.leaderboard.results_log import all_results
    from esoi.optimization.leaderboard.stage_standings import standings
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons import stale_reason
    from esoi.structure.intent_registry.config import load as load_config
    from esoi.structure.intent_registry.registry import load as load_registry
    config = load_config(start=root or HERE)
    metric = next(m for m in load_registry(config).metrics if m.get("metric_id") == METRIC)
    stages, problems = cascade_stages.load_stages(config, metric)
    if problems:
        raise ValueError(f"the cascade of {METRIC} does not parse: {problems}")
    history = {arm: rows for arm, rows in all_results(config.results_path).get(COMPONENT, {}).items() if split_arm(arm)[1]}
    standing = standings(stages, history, today, lambda row: stale_reason(config, COMPONENT, row, True), config.evaluation)
    out = {"metric": METRIC, "cascade": metric.get("cascading_conditionals", ""),
           "rows": {arm: {str(i): dict(row) for i, row in sorted(s.rows.items())} for arm, s in sorted(standing.items()) if s.rows}}
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    written = write_snapshot()
    print(f"{len(written['rows'])} measured arm(s) written to {SNAPSHOT.name}")
