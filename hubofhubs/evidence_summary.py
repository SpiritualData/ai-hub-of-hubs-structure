"""The generated evidence summary of the README: one row per recorded check, read from ``esoi/results.csv``, ``esoi/per_case.csv`` and
``esoi/evidence.csv`` with the esoi library's own statistics, never typed by hand. It is the hub's thin layer over ``esoi.leaderboard``
and ``esoi.evidence_table`` (which keeps one row per solution's first component): here every component of a solution gets its row,
and the plain words (what the check is, where the cases come from, what public research says) come from ``docs/evidence-labels.csv``.
A check with no recorded run does not appear until it has one; ``unmeasured`` lists what is named but has no run, with the reason.
Nothing here calls a model or the network."""
import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional

from esoi import evidence, evidence_table, leaderboard
from esoi.config import Config
from esoi.registry import Registry, harness_arms
from esoi.tables import read_csv

EVIDENCE_BEGIN, EVIDENCE_END = "<!-- evidence:start -->", "<!-- evidence:end -->"
UNMEASURED_BEGIN, UNMEASURED_END = "<!-- unmeasured:start -->", "<!-- unmeasured:end -->"
ARMS_BEGIN, ARMS_END = "<!-- arms:start -->", "<!-- arms:end -->"
HEADLINE_BEGIN, HEADLINE_END = "<!-- headline:start -->", "<!-- headline:end -->"
COMPACT_BEGIN, COMPACT_END = "<!-- headline-compact:start -->", "<!-- headline-compact:end -->"
RESEARCH = "docs/what-public-research-says.md"
HEADER = ["Check (solution, part of the mind)", "What it does", "Common-sense check", "Cases and source", "Selected arm", "Pass rate (95% interval)",
          "Cost per passing case", "Is the lead real?", "What public research says"]
Row = Dict[str, str]


def labels(root: Path) -> List[Row]:
    return read_csv(root / "docs" / "evidence-labels.csv")


def p_value(text: str) -> str:
    found = re.findall(r"p\s*=\s*([0-9.]+(?:e-?\d+)?)", text)
    return found[-1] if found else ""


def test_name(text: str) -> str:
    return "McNemar" if "McNemar" in text else "Fisher" if "Fisher" in text else "sign test" if "sign" in text else "paired test"


def standing(decision: "leaderboard.Decision", rows: Dict[str, Row]) -> str:
    """One short phrase for a rival against the selected arm, with the test and p."""
    p, name = p_value(decision.text), test_name(decision.text)
    if decision.basis != "significance":
        return f"{decision.rival}: best guess only, no per-case rows to test"
    if decision.outcome == "rival":
        row = rows[decision.rival]
        figures = f"{leaderboard.passes(row)}/{row.get('cases')}, {evidence_table.cost_label(row)} per pass"
        return (f"{decision.rival} beats it ({name} p={p}; {figures})" if decision.switch
                else f"{decision.rival} ahead but not significant ({name} p={p})")
    if decision.outcome == "incumbent":
        return f"ahead of {decision.rival} ({name} p={p})"
    return f"not separated from {decision.rival} ({name} p={p}, {decision.disagree} of {decision.shared} cases differ)"


def component_solutions(config: Config, registry: Registry) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for sol in registry.solutions:
        for component, _ in harness_arms(config, sol.get("metric_command", "")):
            out.setdefault(component, sol["solution_id"])
    return out


def latest_whole(history: Dict[str, List[Row]]) -> Dict[str, Row]:
    found = {impl: [r for r in rows if not leaderboard.is_partial(r)] for impl, rows in history.items()}
    return {impl: rows[-1] for impl, rows in found.items() if rows}


def research_cell(config: Config, registry: Registry, graded: Dict, solution_id: str, impl: str, label: Row) -> str:
    keys = evidence.implementation_candidates(config, registry, solution_id).get(impl, "")
    letters = sorted({e.grade for e in evidence.lines_for_implementation(graded, keys)}) if keys else []
    own = f"graded public numbers for this arm: {', '.join(letters)}" if letters else "no graded public number for this arm"
    link = f"[{label['research']}]({RESEARCH}#{label['anchor']})" if label["anchor"] else label["research"]
    return f"{link}; {own}"


def check_rows(config: Config, registry: Registry, root: Path, today: Optional[datetime.date] = None) -> List[Row]:
    history = leaderboard.all_results(config.results_path)
    per_case = leaderboard.per_case_rows(config)
    chosen = leaderboard.policies(config, registry, per_case)
    selected_of = leaderboard.selected_impls(config, registry.solutions)
    owner = component_solutions(config, registry)
    solutions = {s["solution_id"]: s for s in registry.solutions + registry.specifications}
    try:
        graded = evidence.estimates(evidence.load_for(config), today)
    except evidence.EvidenceError:
        graded = {}
    out: List[Row] = []
    described = {x["key"]: x for x in labels(root) if x["kind"] == "check"}
    for component in [*described, *sorted(set(history) - set(described))]:   # a recorded check nobody described still appears
        if component not in history:
            continue
        label = described.get(component) or {"key": component, "seat": "", "check": "No plain-words description yet: add a row to docs/evidence-labels.csv.",
                                             "cases": "{n} cases", "research": "not linked yet", "anchor": "", "reason": ""}
        sid = owner.get(component) or label["seat"]
        rows = latest_whole(history[component])
        if not rows:
            continue
        selected = selected_of.get(component, "")
        apart = bool(leaderboard.invariant_reason(component, config.evaluation))
        seat = solutions.get(label["seat"], {})
        words = solutions.get(sid, {}).get("purpose", "")
        lead, arm_cell, rate, cost = "", "", "", ""
        if apart:
            arm_cell = "none: arms are complementary, not ranked"
            rate = "; ".join(f"{impl} {evidence_table.rate_label(row)}" for impl, row in sorted(rows.items()))
            cost = "; ".join(f"{impl} {evidence_table.cost_label(row)}" for impl, row in sorted(rows.items()))
            lead = "not ranked: " + label["reason"]
        elif selected in rows:
            pairs = {r["impl"]: (own, r) for own, r in leaderboard.rival_pairs(rows, selected, config.evaluation, history[component])[0]}
            row = next(iter(pairs.values()))[0] if pairs else rows[selected]
            found = leaderboard.decisions(rows, selected, config.evaluation, history[component], per_case, chosen.get(component))
            arm_cell = selected
            rate, cost = evidence_table.rate_label(row), evidence_table.cost_label(row)
            lead = "; ".join(standing(d, rows) for d in found) or "no rival measured on the same cases, so no lead to test"
            if any(d.outcome == "rival" and d.switch for d in found):
                lead += "; the selected arm is the floor and selection is pending"
            for impl, why in leaderboard.incomparable_rivals(rows, selected, config.evaluation, history[component]):
                lead += f"; {impl} not comparable ({why})"
        else:
            impl, text = leaderboard.best_guess(rows, config.evaluation)
            row = rows[impl] if impl in rows else next(iter(rows.values()))
            arm_cell = f"{row['impl']} (best guess, none selected)"
            rate, cost = evidence_table.rate_label(row), evidence_table.cost_label(row)
            lead = "best guess: only one arm measured, no test possible"
        shown = selected if selected in rows else next(iter(rows))
        out.append({"check": f"`{sid or component}`" + (f", {seat.get('name', '').split(': the ')[-1].replace(' seat', '')}" if seat and ': the ' in seat.get("name", "") else ""),
                    "does": words, "test": label["check"], "cases": label["cases"].replace("{n}", str(rows[shown].get("cases", ""))),
                    "arm": arm_cell, "rate": rate, "cost": cost, "lead": lead,
                    "research": research_cell(config, registry, graded, sid, shown, label)})
    return out


def evidence_block(config: Config, registry: Registry, root: Path, today: Optional[datetime.date] = None) -> str:
    rows = check_rows(config, registry, root, today)
    if not rows:
        return "No check has a recorded run yet."
    lines = ["| " + " | ".join(HEADER) + " |", "|" + "---|" * len(HEADER)]
    for r in rows:
        cells = [r["check"], r["does"], r["test"], r["cases"], r["arm"], r["rate"], r["cost"], r["lead"], r["research"]]
        lines.append("| " + " | ".join(evidence_table.cell(c) for c in cells) + " |")
    lines += ["", "A lead is real only when a one-sided exact paired test on the same cases gives p below 0.05 after Holm's correction; "
              "otherwise the selected arm stays and the cell says how many cases the arms disagree on. "
              "Every arm of every check is in [docs/evidence-by-arm.md](docs/evidence-by-arm.md)."]
    return "\n".join(lines)


def arms_block(config: Config, registry: Registry, today: Optional[datetime.date] = None) -> str:
    """Every arm of every recorded component, the library's table rows over all components and not only each solution's first."""
    history = leaderboard.all_results(config.results_path)
    per_case = leaderboard.per_case_rows(config)
    chosen = leaderboard.policies(config, registry, per_case)
    selected_of = leaderboard.selected_impls(config, registry.solutions)
    owner = component_solutions(config, registry)
    try:
        graded = evidence.estimates(evidence.load_for(config), today)
    except evidence.EvidenceError:
        graded = {}
    lines = ["| Component | Arm | Cases | Pass rate (95% Wilson) | Cost per passing case | Seconds per case | Versus the selected arm | Public evidence (not in our numbers) |",
             "|---|---|---|---|---|---|---|---|"]
    for component in sorted(history):
        rows = latest_whole(history[component])
        if not rows:
            continue
        selected = selected_of.get(component, "")
        apart = bool(leaderboard.invariant_reason(component, config.evaluation))
        found = {d.rival: d for d in leaderboard.decisions(rows, selected, config.evaluation, history[component], per_case, chosen.get(component))} \
            if selected in rows and not apart else {}
        for impl in sorted(rows, key=lambda i: (i != selected, i)):
            row = rows[impl]
            if apart:
                versus = "complementary arm, not ranked"
            elif impl == selected:
                versus = "selected"
            elif impl in found:
                versus = standing(found[impl], rows)
            else:
                versus = "not compared: no run on the same cases as the selected arm"
            cells = [component, impl + (" (selected)" if impl == selected else ""), str(row.get("cases", "")), evidence_table.rate_label(row),
                     evidence_table.cost_label(row), evidence_table.seconds_label(row, per_case), versus,
                     evidence_table.public_label(config, registry, graded, owner.get(component, ""), impl)]
            lines.append("| " + " | ".join(evidence_table.cell(c) for c in cells) + " |")
    return "\n".join(lines)


def unmeasured_block(config: Config, registry: Registry, root: Path) -> str:
    """What is named but has no run: mind seats with no measured solution, and arms a metric names that have no recorded row."""
    history = leaderboard.all_results(config.results_path)
    reasons = {x["key"]: x["reason"] for x in labels(root) if x["kind"] == "gap"}
    waived = {w["path"]: w["reason"] for w in registry.waivers if w.get("rule") == "S24"}   # a waiver already says why an arm has no run
    measured_seats = {x["seat"] for x in labels(root) if x["kind"] == "check" and x["key"] in history}
    lines = []
    for sol in registry.every_solution():
        match = re.fullmatch(r"[a-z-]+: the (.+) seat", sol.get("name", ""))
        if match and sol["solution_id"] not in measured_seats:
            why = reasons.get(sol["solution_id"], "no check is written yet")
            lines.append(f"- **`{sol['solution_id']}`** ({match.group(1)}): not measured. {why}")
        elif match and f"{sol['solution_id']}:rest" in reasons:
            lines.append(f"- **`{sol['solution_id']}`** ({match.group(1)}): measured in part. {reasons[sol['solution_id'] + ':rest']}")
    grouped: Dict[tuple, List[str]] = {}
    for sol in registry.solutions:
        for component, impl in harness_arms(config, sol.get("metric_command", "")):
            if impl not in history.get(component, {}):
                why = reasons.get(f"{component}:{impl}") or reasons.get(component) or waived.get(f"{sol['solution_id']}:{impl}") or "No run is recorded yet."
                grouped.setdefault((sol["solution_id"], why), []).append(f"`{impl}`" + (f" ({component})" if component != sol["solution_id"].replace("-", "_") else ""))
    for (sid, why), arms in grouped.items():
        lines.append(f"- **`{sid}`**, arms with no run: {', '.join(dict.fromkeys(arms))}. {why}")
    return "\n".join(lines) or "Every named seat and arm has a recorded run."


def counted_arms(config: Config, root: Path) -> Dict[str, List[str]]:
    """``{area: [arm, ...]}``: the distinct real alternatives with a recorded whole run, by the area label of their check
    (``docs/evidence-labels.csv``). Left out: a check with no area label (mechanics such as the single-scenario assembly), and any arm
    that marks itself a baseline, floor, ablation or validity reference in its module docstring (``none``, ``single_provider``)."""
    history = leaderboard.all_results(config.results_path)
    out: Dict[str, List[str]] = {}
    for label in labels(root):
        area = label.get("area", "")
        if label["kind"] != "check" or not area or label["key"] not in history:
            continue
        for impl, row in latest_whole(history[label["key"]]).items():
            if leaderboard.arm_kind(row, config.evaluation) in ("", "alternative") and impl not in out.setdefault(area, []):
                out[area].append(impl)
    return {area: sorted(arms) for area, arms in out.items() if arms}


def headline_block(config: Config, registry: Registry, root: Path) -> str:
    """The README headline and the per-area count table, computed from the results log and the registry."""
    areas = counted_arms(config, root)
    total = sum(len(arms) for arms in areas.values())
    candidates = len(read_csv(root / "hubofhubs" / "registry" / "hub_findings.csv"))
    lines = [f"**{total} alternatives measured across {len(areas)} areas, from {candidates} researched candidates.**", "",
             "| Area | Alternatives measured | Which |", "|---|---|---|"]
    order = [x.get("area", "") for x in labels(root) if x["kind"] == "check"]
    for area in sorted(areas, key=lambda a: order.index(a)):
        lines.append(f"| {area} | {len(areas[area])} | {', '.join('`' + a + '`' for a in areas[area])} |")
    lines += ["", "Counted: distinct arms with a recorded run on the same cases as their rivals. Not counted: baselines and floors "
              "(such as `none` and `single_provider`) and single-scenario mechanics checks ([how we measure](docs/how-we-measure.md#what-counts-as-an-alternative))."]
    return "\n".join(lines)


def compact_headline(config: Config, root: Path) -> str:
    """The headline as one paragraph for a post or an article: the totals, then the count per area."""
    areas = counted_arms(config, root)
    candidates = len(read_csv(root / "hubofhubs" / "registry" / "hub_findings.csv"))
    per_area = ", ".join(f"{area} {len(arms)}" for area, arms in areas.items())
    return f"{sum(len(a) for a in areas.values())} alternatives measured across {len(areas)} areas, from {candidates} researched candidates. By area: {per_area}."
