"""Each tier's default model from its own metric over public evaluations, price and speed.

Pure functions over two data files: ``tier_metrics.csv`` beside this file (the fixed minimum scores, the factor weights, the bonus weights, the
fit of each evaluation and the freshness, each with its reason, written before any ranking) and ``registry/tier_public_scores.csv`` (one row per
model and reasoning effort with the public numbers, their source URL and the date checked). No model call, no network, no clock (the day is an
argument), no environment.

The form: the cheapest and fastest model that is good enough.

* An arm is eligible when it has a current number on every evaluation the tier names, a list price and a published output speed.
* The minimum of a tier is what does the tier's job today: for each evaluation the tier names, the score of the tier's held default (the anchor) at its
  documented default effort, less a tolerance (5 percent of the score). An arm clears the tier when it reaches every minimum, so the held default
  always clears its own. An evaluation on which the anchor has no current number is dropped (and listed), never guessed. Best has no minimum.
* Among the arms that clear, ``score = K^wc x S^ws x (1 + bonus x C)`` where ``K`` is the cheapest clearing arm's list price divided by the arm's
  (input plus output USD per million tokens), ``S`` is the arm's output speed divided by the fastest clearing arm's, ``wc + ws = 1``, and ``C`` in
  0 to 1 is the weighted share of the best value on the tier's evaluations (an Elo rating is read as the chance of beating the best arm). The bonus is
  small and grows by tier, so capability above the minimum never outweighs a large price difference.
* Best uses ``C`` alone: cost and speed are not factors.

Nothing is imputed: a missing number makes the arm ineligible. A row older than the freshness days is not used. An arm at an effort other than the
model's documented default is eligible only when the caller applies the effort. A tier whose evaluations are mostly proxies says so in its result.
"""
import csv
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_world.learning.research_freshness_reader import registry

METRICS = Path(__file__).with_name("tier_metrics.csv")
SCORES = "tier_public_scores.csv"
SOURCE = "artificial_analysis"
TIERS = ("fast", "balanced", "quality", "best")
ELO = ("aa_briefcase", "gdpval_aa")          # measures published as Elo ratings: read as the chance of beating the best arm
SPEED = "output_speed_tps"
STRING_KEYS = ("provider", "model", "effort", "is_default", "default_source", "source", "source_url", "source_date", "checked_on")


def number(text: Any) -> Optional[float]:
    try:
        return float(text) if str(text).strip() != "" else None
    except (TypeError, ValueError):
        return None


def read_metrics(path: Path = METRICS) -> List[Dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def metric_for(rows: Sequence[Mapping[str, str]], tier: str, role: str = "") -> Dict[str, Any]:
    """``{capability: {measure: weight}, factors: {cost, speed, bonus | capability: weight}, fit: {measure: fit}}`` for a tier (the evaluations it names,
    each of which gets a minimum from the anchor). A role (a domain of call, for example ``science``) that has capability rows for the tier replaces
    the tier's capability weights and factors with its own, each part falling back to the tier's when the role has none."""
    def part(name, role_name):
        return [r for r in rows if r["tier"] == tier and r["part"] == name and r["role"] == role_name]
    use = role if role and part("capability", role) else ""
    out: Dict[str, Any] = {"role": use, "capability": {}, "factors": {}, "fit": {}}
    for name, key in (("capability", "capability"), ("factor", "factors")):
        for r in part(name, use) or part(name, ""):
            out[key][r["measure"]] = number(r["weight"]) or 0.0
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
    return [{k: (v if k in STRING_KEYS else number(v)) for k, v in r.items()} for r in score_rows(folder) if r["source"] == source]


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


def rank(arms: Sequence[Mapping[str, Any]], metric: Mapping[str, Any], today: str, max_age_days: float = 45, effort_providers: Sequence[str] = (),
         rate: Optional[Callable[[str, str], Optional[Sequence[float]]]] = None, anchor: Optional[Mapping[str, Any]] = None,
         tolerance: float = 0.05) -> Dict[str, Any]:
    """Rank the arms of one tier: ``{ranking, excluded, minimums, dropped}``. ``rate(provider, model)`` gives the list price (input, output) in USD per
    million tokens or None. ``anchor`` is the public row of the tier's held default at its default effort: each evaluation's minimum is the anchor's score
    less ``tolerance`` of it; an evaluation the anchor has no number on is dropped (listed in ``dropped``) and its weight shared among the others. A tier
    with cost and speed factors and no anchor ranks nothing. A ranked row has ``score``, ``capability`` (the 0 to 1 share), ``cost_factor``,
    ``speed_factor`` and the raw ``values``; an excluded row has ``why``. Highest score first; the cheaper arm first on an exact tie."""
    factors = metric["factors"]
    priced = factors.get("cost", 0) > 0 or factors.get("speed", 0) > 0
    if priced and anchor is None:
        return dict(ranking=[], excluded=[], minimums={}, dropped=[], why="the tier's held default has no current public row to anchor the minimums")
    dropped = [m for m in metric["capability"] if priced and anchor.get(m) is None]
    kept = {m: w for m, w in metric["capability"].items() if m not in dropped}
    share = sum(kept.values()) or 1.0
    caps = {m: w / share for m, w in kept.items()}
    minimums = {m: anchor[m] * (1 - tolerance) for m in caps} if priced else {}
    judged = list(caps)
    excluded, eligible = [], []
    for a in arms:
        age = age_days(a, today)
        price = rate(a["provider"], a["model"]) if (priced and rate) else None
        why = ""
        if age is None or age > max_age_days:
            why = f"public row older than {max_age_days:g} days or undated"
        elif a.get("is_default") != "yes" and a["provider"] not in effort_providers:
            why = "effort not applied by the caller"
        else:
            missing = [m for m in judged if a.get(m) is None]
            if priced and not price:
                missing.append("list price")
            if priced and not (a.get(SPEED) or 0) > 0:
                missing.append(SPEED)
            if missing:
                why = "no number for " + ", ".join(missing)
        (excluded if why else eligible).append(dict(provider=a["provider"], model=a["model"], effort=a["effort"], why=why, row=a, price=sum(price) if price else None))
    base = lambda e: dict(provider=e["provider"], model=e["model"], effort=e["effort"])
    best = {m: max((e["row"][m] for e in eligible), default=0.0) for m in caps}
    clearing = []
    for e in eligible:
        under = [f"{m} {e['row'][m]:g} < {v:g}" for m, v in minimums.items() if e["row"][m] < v]
        if under:
            excluded.append(dict(base(e), why="below the minimum: " + "; ".join(under)))
        else:
            e["capability"] = sum(w * normalise(m, e["row"][m], best[m]) for m, w in caps.items())
            clearing.append(e)
    ranked = []
    cheapest = min((e["price"] for e in clearing if e["price"]), default=None)
    fastest = max((e["row"].get(SPEED) or 0 for e in clearing), default=None)
    for e in clearing:
        cost_f = cheapest / e["price"] if priced and e["price"] else 1.0
        speed_f = (e["row"][SPEED] / fastest) if priced and fastest else 1.0
        score = ((cost_f ** factors.get("cost", 0.0)) * (speed_f ** factors.get("speed", 0.0)) * (1 + factors.get("bonus", 0.0) * e["capability"])
                 if priced else e["capability"])
        values = {m: e["row"][m] for m in judged}
        values.update(list_price_sum_usd_per_mtok=e["price"], output_speed_tps=e["row"].get(SPEED))
        ranked.append(dict(base(e), score=score, capability=e["capability"], cost_factor=cost_f, speed_factor=speed_f, values=values))
    ranked.sort(key=lambda s: (-s["score"], s["values"].get("list_price_sum_usd_per_mtok") or 0.0))
    return dict(ranking=ranked, excluded=excluded, minimums=minimums, dropped=dropped)


def reason(tier: str, got: Mapping[str, Any], metric: Mapping[str, Any], evidence: str) -> str:
    top = got["ranking"][0]
    role = f" for the role {metric['role']}" if metric["role"] else ""
    proxy = "proxy evidence: " if evidence == "proxy" else ""
    parts = f"capability share {top['capability']:.3f}"
    if metric["factors"].get("cost"):
        parts += (f", list price {top['values']['list_price_sum_usd_per_mtok']:g} USD per million tokens in plus out (cost factor {top['cost_factor']:.3f}),"
                  f" output speed {top['values']['output_speed_tps']:g} tokens per second (speed factor {top['speed_factor']:.3f})")
    nxt = next((s for s in got["ranking"][1:] if (s["provider"], s["model"]) != (top["provider"], top["model"])), None)
    tail = f"; runner-up {nxt['provider']}/{nxt['model']} at {nxt['effort']} ({nxt['score']:.3f})" if nxt else ""
    return f"{proxy}public metric of the {tier} tier{role}: score {top['score']:.3f}, {len(got['ranking'])} arm(s) clear the minimums ({parts}){tail}"


def choose_public(tier: str, folder: Any = None, available: Optional[Sequence[str]] = None, today: str = "", role: str = "", rows: Optional[Sequence[Mapping[str, str]]] = None,
                  arms: Optional[Sequence[Mapping[str, Any]]] = None, effort_providers: Sequence[str] = (),
                  rate: Optional[Callable[[str, str], Optional[Sequence[float]]]] = None, anchor: Optional[Sequence[str]] = None) -> Optional[Dict[str, Any]]:
    """The public choice of one tier: ``{arm, effort, reason, ranking, excluded, stage, evidence, role, minimums, dropped, anchor}`` or None when no arm
    clears the tier's anchored minimums on current numbers. ``anchor`` is the (provider, model) of the tier's held default. ``evidence`` is ``proxy`` when evaluations marked direct carry under half of the capability weight. ``available`` limits the
    providers; ``effort_providers`` names the providers whose caller applies the effort returned; ``rate`` gives list prices; ``today`` is an ISO date."""
    rows = read_metrics() if rows is None else rows
    metric = metric_for(rows, tier, role)
    if not metric["capability"]:
        return None
    everyone = candidates(folder) if arms is None else list(arms)
    pool = [a for a in everyone if available is None or a["provider"] in available]
    max_age = setting(rows, "freshness", "scores", 45)
    # the anchor is the held default's row at its default effort, whether or not this install can call it: it says what does the tier's job today
    anchor_row = next((a for a in everyone if anchor and (a["provider"], a["model"]) == tuple(anchor) and a.get("is_default") == "yes"
                       and age_days(a, today) is not None and age_days(a, today) <= max_age), None)
    got = rank(pool, metric, today, max_age, effort_providers, rate, anchor_row, setting(rows, "rule", "tolerance", 0.05))
    if not got["ranking"]:
        return None
    evidence = "direct" if direct_share(metric) >= 0.5 else "proxy"
    top = got["ranking"][0]
    return dict(arm=(top["provider"], top["model"]), effort=top["effort"], reason=reason(tier, got, metric, evidence), ranking=got["ranking"], excluded=got["excluded"],
                stage="public", evidence=evidence, role=metric["role"], minimums=got["minimums"], dropped=got["dropped"],
                anchor=dict(arm=tuple(anchor), effort=anchor_row["effort"]) if anchor_row else None)
