"""Which arm of Delegated Agent Sessions a consumer gets, among the arms it can run.

An arm is ``<harness>@provider=<provider>,tier=<tier>`` (an esoi variant name, the same string as the ``impl`` of a results row). A
consumer declares the providers it holds credentials for; an arm is eligible when its provider is one of them and its harness can drive
that provider (``PROVIDERS`` on the harness class, see ``providers``). The choice, in order:

1. **measured**: the esoi cascade rule (``esoi.optimization.leaderboard.stage_standings.decide``) applied to the eligible arms only: the best
   result at the latest stage any of them reached, unless another eligible arm beat it at an earlier shared stage and has not been run
   at the latest one. The results come from the snapshot ``arm_standings.json`` beside this file, written from the results log by
   ``write_snapshot`` so an installed copy needs no records (``python3 -m hubofhubs.the_world.tools.delegated_agent_sessions.arm_choice``).
2. **public prior**: with no measured eligible arm, the eligible arm whose prior in ``public_priors.csv`` (evidence graded C or better)
   has the highest balanced score: the same ``[balance.agent_sessions]`` weights and budgets as the measured stage, with the prior as the
   pass rate and the row's ``cost_per_case_usd`` and ``seconds_per_case`` when it states them. A row that states no cost or time scores
   nothing on that part, since an unknown price is never counted as free. Labelled with its grade.
3. **idea**: else the eligible arm with the highest idea-stage rating in ``arm_ideas.csv`` (the scale is ``esoi/idea-rating-scale.md``).

A kind of work with a metric of its own (``KINDS``: hard deep work, measured on real past deep tasks) is chosen from that metric's results
when the caller names it (``difficulty="hard"``) and an eligible arm is measured there; otherwise the choice above stands.

**Harnesses are compared on the same model only.** An arm is a harness on a model, so a result that differs in both says nothing about either
alone. ``harness_ranking`` ranks harnesses per model, from the rows that ran that model, and never across models; a measured choice names every
other harness it was not compared with on a shared model (``ArmChoice.uncompared``) and the run that would settle it. Arms of one harness on
different models are a choice of model, which is the tier chooser's question, and stay comparable.

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
#: kinds of work measured on a metric of their own: {difficulty: (metric id, component)}. A consumer that knows a run's difficulty asks
#: for that kind; with no measured eligible arm for it, the choice for ordinary work stands.
KINDS = {"hard": ("metric-delegated-agent-sessions-hard", "agent_sessions_hard")}
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
    kind: str = ""        # the kind of work whose own metric decided (``KINDS``), "" for ordinary work
    uncompared: Tuple[str, ...] = ()   # harnesses never measured on a model this arm's harness was measured on: not beaten, not compared


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
    """Whether a consumer that holds credentials for ``declared`` providers can run ``arm``: its provider is declared and its harness drives it. Whether an arm
    has earned selection is the metric's stage result (``selection_stages``), never a flag on the harness."""
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


def latest_row(by_stage: Dict[Any, Dict[str, Any]]) -> Dict[str, Any]:
    return dict(by_stage[max(by_stage, key=lambda i: int(i))]) if by_stage else {}


def harness_ranking(rows: Dict[str, Dict[Any, Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """``{model: [{"harness", "arm", "balanced", "passed", "cases"} best first]}`` for every model at least two harnesses ran: the only tables in
    which one harness is ranked against another. A harness with several arms on a model is listed once, by its best."""
    by_model: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for arm, by_stage in (rows or {}).items():
        row = latest_row(by_stage)
        model, harness = str(row.get("model") or "").strip(), split_arm(arm)[0]
        if not model:
            continue
        entry = {"harness": harness, "arm": arm, "balanced": number(row.get("balanced")) or 0.0, "passed": row.get("passed", ""), "cases": row.get("cases", "")}
        held = by_model.setdefault(model, {})
        if harness not in held or entry["balanced"] > held[harness]["balanced"]:
            held[harness] = entry
    return {model: sorted(held.values(), key=lambda e: -e["balanced"]) for model, held in sorted(by_model.items()) if len(held) > 1}


def models_of(rows: Dict[str, Dict[Any, Dict[str, Any]]]) -> Dict[str, set]:
    """``{harness: the models it has a result on}``."""
    out: Dict[str, set] = {}
    for arm, by_stage in (rows or {}).items():
        model = str(latest_row(by_stage).get("model") or "").strip()
        if model:
            out.setdefault(split_arm(arm)[0], set()).add(model)
    return out


def missing_same_model_runs(rows: Dict[str, Dict[Any, Dict[str, Any]]]) -> List[str]:
    """The runs that would let every pair of measured harnesses be compared: for each pair with no model in common, the pair and the models
    either one has a result on (run the other there)."""
    models = models_of(rows)
    names = sorted(models)
    return [f"{a} and {b} share no model: run {b} on {', '.join(sorted(models[a]))} or {a} on {', '.join(sorted(models[b]))}"
            for i, a in enumerate(names) for b in names[i + 1:] if not models[a] & models[b]]


def measured_choice(declared: Iterable[str], snapshot: Dict[str, Any]) -> Optional[ArmChoice]:
    from esoi.optimization.leaderboard import cascade_stages
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
    # The winner beat only the harnesses measured on a model its own harness was measured on. Any other eligible harness was never compared
    # with it (a different harness on a different model is two differences), so it is named, not counted as beaten.
    eligible_rows = {arm: by_stage for arm, by_stage in (snapshot.get("rows") or {}).items() if arm in standing}
    models = models_of(eligible_rows)
    uncompared = tuple(sorted(h for h, ms in models.items() if h != harness and not ms & models.get(harness, set())))
    note = (f"; not compared on the same model with: {', '.join(uncompared)} (a harness is ranked against another only on results with the "
            f"same model)") if uncompared else ""
    return ArmChoice(decision.winner, harness, provider, tier, "measured", stage, number(row.get("balanced")) or 0.0,
                     f"best eligible arm at the {stage} stage ({passed} passed, balanced {row.get('balanced', '?')}){held}{note}",
                     uncompared=uncompared)


def prior_balanced(row: Dict[str, str], balance: Optional[Dict[str, Any]]) -> float:
    """The balanced score of a prior row: the prior as the pass rate, the row's cost and seconds per case where it states them, and
    the whole budget (nothing scored) where it does not."""
    from esoi.optimization.measurement_harness.balance import DEFAULT_WEIGHTS, clamp
    table = balance or {}
    weights = {**DEFAULT_WEIGHTS, **(table.get("weights") or {})}
    cost, seconds = number(row.get("cost_per_case_usd")), number(row.get("seconds_per_case"))
    cost_budget, seconds_budget = number(table.get("cost_per_case_usd")), number(table.get("seconds_per_case"))
    cost_part = clamp(1 - cost / cost_budget) if cost is not None and cost_budget else 0.0
    time_part = clamp(1 - seconds / seconds_budget) if seconds is not None and seconds_budget else 0.0
    return weights["accuracy"] * (number(row.get("prior")) or 0.0) + weights["cost"] * cost_part + weights["time"] * time_part


def prior_choice(declared: Iterable[str], rows: List[Dict[str, str]], balance: Optional[Dict[str, Any]] = None) -> Optional[ArmChoice]:
    usable = [r for r in rows if (r.get("grade") or "").strip().upper()[:1] in USABLE_GRADES and number(r.get("prior")) is not None
              and eligible(r.get("arm_id", ""), declared)]
    if not usable:
        return None
    best = max(usable, key=lambda r: prior_balanced(r, balance))
    harness, provider, tier = split_arm(best["arm_id"])
    score = prior_balanced(best, balance)
    return ArmChoice(best["arm_id"], harness, provider, tier, "public prior", "public", score,
                     f"no eligible arm is measured; best balanced score on public priors {score:.3f} (prior {best['prior']}, grade "
                     f"{best['grade']}): {best.get('reason', '')}".strip())


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


def stage_choice(declared: Iterable[str], stages: Dict[str, Any]) -> Optional[ArmChoice]:
    """The metric's own selection (``selection_stages.decide``: the open-ended and hard floors, repeated runs, pass rate first and cost within noise)
    among the arms this consumer can run, from the counting whole runs in the snapshot's ``stages``; None when no arm it can run is selectable."""
    from hubofhubs.the_world.tools.delegated_agent_sessions import selection_stages
    runs = {key: {arm: rows for arm, rows in (stages.get(key) or {}).items() if eligible(arm, declared)} for key in ("open", "hard", "real")}
    arms = sorted(set(runs["open"]) | set(runs["hard"]))
    verdict = selection_stages.decide(runs["open"], runs["hard"], runs["real"], arms)
    if not verdict.winner:
        return None
    harness, provider, tier = split_arm(verdict.winner)
    rows = runs["hard"][verdict.winner]
    return ArmChoice(verdict.winner, harness, provider, tier, "measured", "hard", selection_stages.rate(rows),
                     f"selected by the metric's stages: {verdict.reason}")


def choose_agent_arm(declared: Iterable[str], *, difficulty: str = "", snapshot: Optional[Dict[str, Any]] = None,
                     priors: Optional[List[Dict[str, str]]] = None, ideas: Optional[List[Dict[str, str]]] = None) -> Optional[ArmChoice]:
    """The arm for a consumer holding credentials for ``declared`` providers, or None when it can run no arm. ``difficulty`` names a kind
    of work measured on its own metric (``KINDS``, e.g. ``"hard"``): its best measured eligible arm is chosen when there is one, else the
    choice for ordinary work."""
    declared = providers.normalise_all(declared)
    snapshot = read_snapshot() if snapshot is None else snapshot
    staged = stage_choice(declared, snapshot.get("stages") or {})
    if staged is not None:
        return staged
    kind = (snapshot.get("kinds") or {}).get((difficulty or "").strip().lower())
    if kind:
        chosen = measured_choice(declared, kind)
        if chosen is not None:
            chosen.reason = f"for {difficulty} work: {chosen.reason}"
            chosen.kind = difficulty.strip().lower()
            return chosen
    return (measured_choice(declared, snapshot)
            or prior_choice(declared, read_rows(PRIORS) if priors is None else priors, snapshot.get("balance"))
            or idea_choice(declared, read_rows(IDEAS) if ideas is None else ideas))


def build_agent_runner(choice: ArmChoice, config: Any, **arguments: Any) -> Any:
    """An instance of the chosen arm: its harness class built from ``config`` with the arm's provider and tier (and any other
    constructor ``arguments`` the consumer passes, such as ``settings``)."""
    cls = harness_class(choice.harness)
    if cls is None:
        raise ValueError(f"the hub declares no harness {choice.harness!r}")
    return cls(config, provider=choice.provider, tier=choice.tier, **arguments)


def balance_table(config: Any, component: str = COMPONENT) -> Dict[str, Any]:
    """``[balance.<component>]`` of the configuration file (weights and budgets), or ``{}``."""
    try:
        import tomllib
    except ImportError:   # Python 3.10
        return {}
    try:
        with (Path(config.root) / "esoi.toml").open("rb") as handle:
            return dict((tomllib.load(handle).get("balance") or {}).get(component) or {})
    except (OSError, ValueError):
        return {}


def standing_of(config: Any, metric_id: str, component: str, today: Optional[datetime.date]) -> Dict[str, Any]:
    """One metric's cascade, balance and the counting row of every arm at each stage, from the results log of ``component``. Stale and
    expired results are left out, as the cascade rule leaves them out."""
    from esoi.optimization.leaderboard import cascade_stages
    from esoi.optimization.leaderboard.results_log import all_results
    from esoi.optimization.leaderboard.stage_standings import standings
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons import stale_reason
    from esoi.structure.intent_registry.registry import load as load_registry
    metric = next(m for m in load_registry(config).metrics if m.get("metric_id") == metric_id)
    stages, problems = cascade_stages.load_stages(config, metric)
    if problems:
        raise ValueError(f"the cascade of {metric_id} does not parse: {problems}")
    history = {arm: rows for arm, rows in all_results(config.results_path).get(component, {}).items() if split_arm(arm)[1]}
    standing = standings(stages, history, today, lambda row: stale_reason(config, component, row, True), config.evaluation)
    return {"metric": metric_id, "cascade": metric.get("cascading_conditionals", ""), "balance": balance_table(config, component),
            "rows": {arm: {str(i): dict(row) for i, row in sorted(s.rows.items())} for arm, s in sorted(standing.items()) if s.rows}}


def counting_runs(config: Any, component: str) -> Dict[str, List[Dict[str, Any]]]:
    """``{arm: [whole runs]}`` of the component that still describe the code and the cases now on disk (stale ones are left out, as the cascade leaves
    them out), each as the cells the stage rule reads. The newest log keeps every run, so repeated runs are all here."""
    from esoi.optimization.leaderboard.case_identity import cases_digest
    from esoi.optimization.leaderboard.results_log import all_results, is_partial
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons import stale_reason
    now = cases_digest(component, config.evaluation)
    out: Dict[str, List[Dict[str, Any]]] = {}
    for arm, rows in all_results(config.results_path).get(component, {}).items():
        if not split_arm(arm)[1]:
            continue
        kept = [{key: row.get(key, "") for key in ("passed", "cases", "cost_usd", "seconds", "balanced", "date", "git_sha", "model")}
                for row in rows if not is_partial(row) and not (row.get("sample") or "").strip() and row.get("cases_sha") == now
                and row.get("model") != "unknown" and not stale_reason(config, component, row, True)]
        if kept:
            out[arm] = kept
    return out


def write_snapshot(root: Optional[Path] = None, path: Path = SNAPSHOT, today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """Write what ``choose_agent_arm`` reads: the standing of the main metric, and of each kind of work in ``KINDS``."""
    from esoi.structure.intent_registry.config import load as load_config
    config = load_config(start=root or HERE)
    out = standing_of(config, METRIC, COMPONENT, today)
    out["stages"] = {"open": counting_runs(config, COMPONENT), "hard": counting_runs(config, KINDS["hard"][1]), "real": {}}
    out["kinds"] = {kind: standing_of(config, metric_id, component, today) for kind, (metric_id, component) in KINDS.items()}
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    written = write_snapshot()
    print(f"{len(written['rows'])} measured arm(s) written to {SNAPSHOT.name}; by kind: "
          + ", ".join(f"{k} {len(v['rows'])}" for k, v in written["kinds"].items()))
    for label, table in [("ordinary work", written)] + [(f"{k} work", v) for k, v in written["kinds"].items()]:
        for model, ranked in harness_ranking(table["rows"]).items():
            print(f"{label}, {model}: " + " > ".join(f"{e['harness']} ({e['passed']}/{e['cases']}, balanced {e['balanced']})" for e in ranked))
        for line in missing_same_model_runs(table["rows"]):
            print(f"{label}, not comparable yet: {line}")
