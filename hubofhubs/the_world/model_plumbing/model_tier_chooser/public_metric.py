"""The public stage of the tier chooser: each tier's default from its own metric over public evaluations.

Pure functions over two data files: ``tier_metrics.csv`` beside this file (the weights, the factors, the floors and the freshness of each tier, each
with its reason, written before any ranking) and ``registry/tier_public_scores.csv`` (one row per model and reasoning effort with the public numbers,
their source URL and the date they were checked). No model call, no network, no clock (the day is an argument), no environment.

The score of an arm for a tier is ``C^a x K^b x S^c`` with ``a + b + c = 1``:

* ``C``, capability: the weighted mean of the tier's evaluations, each divided by the best value among the arms that have every required number
  (an Elo rating is read as the chance of beating that best arm, scaled so the best is 1);
* ``K``, cost: the lowest cost per task among the arms that clear the floors divided by the arm's cost per task;
* ``S``, speed: the lowest time per task among the arms that clear the floors divided by the arm's.

A tier whose cost and speed factors have weight 0 (best) uses ``C`` alone. A floor is a fraction of the best eligible value of one evaluation (or
of ``C`` itself); an arm under it cannot win however cheap or fast. An arm with no number on a required measure is not eligible: nothing is
imputed. A row older than the tier file's freshness days is not used.
"""
import csv
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_world.learning.research_freshness_reader import registry

METRICS = Path(__file__).with_name("tier_metrics.csv")
SCORES = "tier_public_scores.csv"
SOURCE = "artificial_analysis"
TIERS = ("fast", "balanced", "quality", "best")
ELO = ("aa_briefcase", "gdpval_aa")          # measures published as Elo ratings: read as the chance of beating the best arm
FACTORS = {"cost": "cost_per_task_usd", "speed": "time_per_task_s"}
INFINITE = float("inf")


def number(text: Any) -> Optional[float]:
    try:
        return float(text) if str(text).strip() != "" else None
    except (TypeError, ValueError):
        return None


def read_metrics(path: Path = METRICS) -> List[Dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def metric_for(rows: Sequence[Mapping[str, str]], tier: str, role: str = "") -> Dict[str, Any]:
    """``{capability: {measure: weight}, factors: {capability|cost|speed: weight}, floors: {measure: fraction}}`` for a tier. A role (a domain of
    call, for example ``science``) that has rows for the tier replaces the tier's capability weights; its factors and floors are the role's own when
    it has rows for them, else the tier's."""
    def part(name, role_name):
        return [r for r in rows if r["tier"] == tier and r["part"] == name and r["role"] == role_name]
    use = role if role and part("capability", role) else ""
    out: Dict[str, Any] = {"role": use, "capability": {}, "factors": {}, "floors": {}, "fit": {}}
    for name, key in (("capability", "capability"), ("factor", "factors"), ("floor", "floors")):
        picked = part(name, use) or part(name, "")
        for r in picked:
            out[key][r["measure"]] = number(r["weight"] if name != "floor" else r["minimum"]) or 0.0
            if name == "capability":
                out["fit"][r["measure"]] = r.get("fit") or "proxy"       # no stated fit counts as proxy
    return out


def direct_share(metric: Mapping[str, Any]) -> float:
    """The share of a tier's capability weight carried by evaluations marked direct (they measure the tier's own kind of call)."""
    return sum(w for m, w in metric["capability"].items() if metric["fit"].get(m) == "direct")


def setting(rows: Sequence[Mapping[str, str]], part: str, measure: str, default: float) -> float:
    for r in rows:
        if r["tier"] == "all" and r["part"] == part and r["measure"] == measure:
            return number(r["minimum"]) or default
    return default


def score_rows(folder: Any = None) -> List[Dict[str, str]]:
    """The rows of ``tier_public_scores.csv`` in the registry folder; a folder with no such file has no public numbers."""
    return registry.read(SCORES, folder) if (Path(folder or registry.DATA) / SCORES).exists() else []


def candidates(folder: Any = None, source: str = SOURCE) -> List[Dict[str, Any]]:
    """The public rows of one source as ``{provider, model, effort, numbers..., checked_on, source_url}`` with blank cells as None."""
    out = []
    for r in score_rows(folder):
        if r["source"] == source:
            out.append({k: (v if k in ("provider", "model", "effort", "is_default", "default_source", "source", "source_url", "source_date", "checked_on") else number(v)) for k, v in r.items()})
    return out


def second_source(folder: Any = None) -> Dict[tuple, Dict[str, Optional[float]]]:
    """``{(provider, model): {vals_index, vals_science_index}}`` from the other independent board: a cross-check shown in the breakdown, never scored."""
    out: Dict[tuple, Dict[str, Optional[float]]] = {}
    for r in score_rows(folder):
        if r["source"] != SOURCE:
            out[(r["provider"], r["model"])] = {"vals_index": number(r.get("vals_index")), "vals_science_index": number(r.get("vals_science_index"))}
    return out


def normalise(measure: str, value: float, best: float) -> float:
    """A value as a share of the best: the ratio, or for an Elo rating twice the chance of beating the best arm (1 for the best itself)."""
    if measure in ELO:
        return 2.0 / (1.0 + 10 ** ((best - value) / 400.0))
    return value / best if best > 0 else 0.0


def age_days(row: Mapping[str, Any], today: str) -> Optional[int]:
    try:
        return (date.fromisoformat(today) - date.fromisoformat(row["checked_on"])).days
    except (TypeError, ValueError, KeyError):
        return None


def rank(tier: str, arms: Sequence[Mapping[str, Any]], metric: Mapping[str, Any], today: str, max_age_days: float = 45,
         effort_providers: Sequence[str] = ()) -> Dict[str, Any]:
    """Rank the arms for one tier: ``{ranking: [row...], excluded: [row...]}``. A ranked row has ``score`` and its parts (``capability``, ``cost_factor``,
    ``speed_factor``, the raw ``values``); an excluded row has ``why``. Highest score first; the cheaper arm first on an exact tie."""
    caps, factors, floors = metric["capability"], metric["factors"], metric["floors"]
    judged = list(dict.fromkeys(list(caps) + [m for m in floors if m != "capability"]))     # measures that need a number and a best value
    need = judged + [FACTORS[f] for f in ("cost", "speed") if factors.get(f, 0) > 0]
    excluded, eligible = [], []
    for a in arms:
        age = age_days(a, today)
        why = ""
        if age is None or age > max_age_days:
            why = f"public row older than {max_age_days:g} days or undated"
        elif a.get("is_default") != "yes" and a["provider"] not in effort_providers:
            why = "effort not applied by the caller"
        else:
            missing = [m for m in need if a.get(m) is None or (m in FACTORS.values() and a[m] <= 0)]     # 0 is a score; 0 cost or time is no measurement
            if missing:
                why = "no number for " + ", ".join(missing)
        (excluded if why else eligible).append(dict(provider=a["provider"], model=a["model"], effort=a["effort"], why=why, row=a))
    if not eligible:
        return dict(ranking=[], excluded=[{k: v for k, v in e.items() if k != "row"} for e in excluded])
    best = {m: max(e["row"][m] for e in eligible) for m in judged}
    scored = []
    for e in eligible:
        row = e["row"]
        c = sum(w * normalise(m, row[m], best[m]) for m, w in caps.items())
        scored.append(dict(provider=e["provider"], model=e["model"], effort=e["effort"], capability=c, values={m: row[m] for m in need}, row=row))
    best_c = max(s["capability"] for s in scored)
    kept = []
    for s in scored:
        under = [m for m, f in floors.items() if (s["capability"] < f * best_c if m == "capability" else s["row"][m] < f * best[m])]
        if under:
            excluded.append(dict(provider=s["provider"], model=s["model"], effort=s["effort"], why="below the floor on " + ", ".join(under)))
        else:
            kept.append(s)
    lows = {f: min((k["values"][FACTORS[f]] for k in kept), default=None) for f in FACTORS if factors.get(f, 0) > 0}
    for s in kept:
        cost_f = lows["cost"] / s["values"][FACTORS["cost"]] if "cost" in lows else 1.0
        speed_f = lows["speed"] / s["values"][FACTORS["speed"]] if "speed" in lows else 1.0
        s.update(cost_factor=cost_f, speed_factor=speed_f,
                 score=(s["capability"] ** factors.get("capability", 1.0)) * (cost_f ** factors.get("cost", 0.0)) * (speed_f ** factors.get("speed", 0.0)))
    for s in kept:
        s.pop("row")
    kept.sort(key=lambda s: (-s["score"], s["values"].get(FACTORS["cost"], 0.0)))
    return dict(ranking=kept, excluded=excluded)


def reason(tier: str, got: Mapping[str, Any], metric: Mapping[str, Any]) -> str:
    top = got["ranking"][0]
    parts = f"capability {top['capability']:.3f}"
    if metric["factors"].get("cost"):
        parts += f", cost factor {top['cost_factor']:.3f} (cost per task {top['values'][FACTORS['cost']]:.4g} USD)"
    if metric["factors"].get("speed"):
        parts += f", speed factor {top['speed_factor']:.3f} (time per task {top['values'][FACTORS['speed']]:.0f} s)"
    role = f" for the role {metric['role']}" if metric["role"] else ""
    nxt = next((s for s in got["ranking"][1:] if (s["provider"], s["model"]) != (top["provider"], top["model"])), None)
    tail = f"; runner-up {nxt['provider']}/{nxt['model']} at {nxt['effort']} ({nxt['score']:.3f})" if nxt else ""
    return f"public metric of the {tier} tier{role}: score {top['score']:.3f} ({parts}){tail}"


def choose_public(tier: str, folder: Any = None, available: Optional[Sequence[str]] = None, today: str = "", role: str = "", rows: Optional[Sequence[Mapping[str, str]]] = None,
                  arms: Optional[Sequence[Mapping[str, Any]]] = None, effort_providers: Sequence[str] = ()) -> Optional[Dict[str, Any]]:
    """The public-stage ranking of one tier: ``{arm, effort, reason, ranking, excluded, stage, selects}`` or None when no arm has current numbers.
    ``selects`` is false when the evaluations that fit the tier's use (marked direct) carry too little of its capability weight: the ranking is then
    for information and the caller keeps the held default. ``available`` limits the providers; ``effort_providers`` names the providers whose caller
    applies the effort returned (an arm at a non-default effort of any other provider is not eligible); ``today`` is an ISO date the caller gives."""
    rows = read_metrics() if rows is None else rows
    metric = metric_for(rows, tier, role)
    if not metric["capability"]:
        return None
    pool = [a for a in (candidates(folder) if arms is None else arms) if available is None or a["provider"] in available]
    got = rank(tier, pool, metric, today, setting(rows, "freshness", "scores", 45), effort_providers)
    if not got["ranking"]:
        return None
    top = got["ranking"][0]
    return dict(arm=(top["provider"], top["model"]), effort=top["effort"], reason=reason(tier, got, metric), ranking=got["ranking"], excluded=got["excluded"],
                stage="public", role=metric["role"], selects=direct_share(metric) >= setting(rows, "rule", "direct_share", 0.5))
