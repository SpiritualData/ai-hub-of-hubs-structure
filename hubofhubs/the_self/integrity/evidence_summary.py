"""The generated evidence summary of the README: one row per recorded check, read from ``esoi/results.csv``, ``esoi/per_case.csv`` and
``esoi/evidence.csv`` with the esoi library's own statistics, never typed by hand. It is the hub's thin layer over ``esoi.leaderboard``
and ``esoi.evidence_table`` (which keeps one row per solution's first component): here every component of a solution gets its row,
and the plain words (what the check is, where the cases come from, what public research says) come from ``docs/reference/evidence-labels.csv``.
A check with no recorded run does not appear until it has one; ``unmeasured`` lists what is named but has no run, with the reason.
Nothing here calls a model or the network."""
import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional

from esoi import cascade, evidence, evidence_table, leaderboard
from esoi import Config
from esoi import Registry, harness_arms
from esoi import split_ids as ids, read_csv

EVIDENCE_BEGIN, EVIDENCE_END = "<!-- evidence:start -->", "<!-- evidence:end -->"
UNMEASURED_BEGIN, UNMEASURED_END = "<!-- unmeasured:start -->", "<!-- unmeasured:end -->"
ARMS_BEGIN, ARMS_END = "<!-- arms:start -->", "<!-- arms:end -->"
LEADERBOARD_BEGIN, LEADERBOARD_END = "<!-- leaderboard:start -->", "<!-- leaderboard:end -->"
HEADLINE_BEGIN, HEADLINE_END = "<!-- headline:start -->", "<!-- headline:end -->"
COMPACT_BEGIN, COMPACT_END = "<!-- headline-compact:start -->", "<!-- headline-compact:end -->"
RESEARCH = "docs/explanation/what-public-research-says.md"
LEAD_SIGNIFICANT = "significant lead: "          # the two labels of the lead column; the rule is docs/explanation/how-we-measure.md
LEAD_GUESS = "best guess, not yet significant: "
Row = Dict[str, str]


def labels(root: Path) -> List[Row]:
    return read_csv(root / "docs" / "reference" / "evidence-labels.csv")


def p_value(text: str) -> str:
    found = re.findall(r"p\s*=\s*([0-9.]+(?:e-?\d+)?)", text)
    return found[-1] if found else ""


def test_name(text: str) -> str:
    return "McNemar" if "McNemar" in text else "Fisher" if "Fisher" in text else "sign test" if "sign" in text else "paired test"


def standing(decision: "leaderboard.Decision", rows: Dict[str, Row]) -> str:
    """One short phrase for a rival against the selected arm on the held-out cases, with the two-sided test and p."""
    p, name = p_value(decision.text), "two-sided " + test_name(decision.text)
    if decision.basis != "significance":
        found = re.search(r": (.+?) on the point estimate", decision.text)
        return f"{decision.rival}: best guess, no per-case rows to test" + (f" ({found.group(1)})" if found else "")
    other = decision.other
    if decision.outcome == "rival":
        figures = f"{leaderboard.passes(other)}/{other.get('cases')}, {evidence_table.cost_label(rows.get(decision.rival, other))} per pass"
        if decision.significant:
            return f"{decision.rival} beats it ({name} p={p}; {figures})"
        return f"{decision.rival} is ahead, not significant ({name} p={p}; {figures})"
    if decision.outcome == "incumbent":
        if decision.significant:
            return f"ahead of {decision.rival} ({name} p={p})"
        return f"ahead of {decision.rival}, not significant ({name} p={p})"
    if not p or decision.disagree == 0:
        return f"identical to {decision.rival} on all {decision.shared} cases"
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


def claim_row(per_case: Optional[List[Row]], row: Row, fraction: float) -> Row:
    """The row a claim shows: the held-out part of the run when a split is set and the per-case log holds that run, else the whole run."""
    if fraction:
        part = leaderboard.part_row(per_case, row, fraction, True)
        if part is not None:
            return part
    return row


def deciding_stage(config: Config, registry: Registry, sid: str, row: Row) -> str:
    """The cascade stage of the solution's metric that a results row is a result of, or an empty string when the metric has no cascade."""
    by_id = {m.get("metric_id", ""): m for m in registry.metrics}
    solution = next((s for s in registry.solutions if s["solution_id"] == sid), {})
    for metric_id in ids(solution.get("metric_ids", "")):
        stages, errors = cascade.load_stages(config, by_id.get(metric_id, {}))
        if stages and not errors:
            index = cascade.stage_index(stages, row)
            return stages[index].name if index is not None else ""
    return ""


def claims(config: Config, registry: Registry, root: Path, today: Optional[datetime.date] = None) -> List[Row]:
    """One record per recorded check: who selects what, the held-out numbers the claim rests on, the two-sided result against each rival,
    and whether the selected arm is the highest on the cases that chose it. Every table and the headline are written from these."""
    history = leaderboard.all_results(config.results_path)
    per_case = leaderboard.per_case_rows(config)
    chosen = leaderboard.policies(config, registry, per_case)
    selected_of = leaderboard.selected_impls(config, registry.solutions, registry)
    owner = component_solutions(config, registry)
    solutions = {s["solution_id"]: s for s in registry.solutions + registry.specifications}
    deciding = {}
    for sol in registry.solutions:
        found = harness_arms(config, sol.get("metric_command", ""))
        if found:
            deciding.setdefault(found[0][0], sol["solution_id"])
    try:
        graded = evidence.estimates(evidence.load_for(config), today)
    except evidence.EvidenceError:
        graded = {}
    described = {x["key"]: x for x in labels(root) if x["kind"] == "check"}
    out: List[Row] = []
    for component in [*described, *sorted(set(history) - set(described))]:
        if component not in history:
            continue
        label = described.get(component) or {"key": component, "seat": "", "check": "No plain-words description yet: add a row to docs/reference/evidence-labels.csv.",
                                             "cases": "{n} cases", "research": "not linked yet", "anchor": "", "reason": "", "area": ""}
        rows = latest_whole(history[component])
        if not rows:
            continue
        sid = owner.get(component) or label["seat"]
        selected = selected_of.get(component, "")
        apart = bool(leaderboard.invariant_reason(component, config.evaluation))
        policy = chosen.get(component) or leaderboard.Policy()
        fraction = policy.holdout
        seat = solutions.get(label["seat"], {})
        record: Row = {"component": component, "solution": sid, "area": label.get("area", ""), "apart": apart, "label": label, "rows": rows,
                       "seat": mind_part(seat), "display": solutions.get(sid, {}).get("name", ""),
                       "does": solutions.get(sid, {}).get("purpose", ""), "selected": selected, "decisions": [], "leader": selected,
                       "deciding": deciding.get(component) == sid, "fraction": fraction, "stage": "", "pending": "",
                       "conformance": "(this repo)" in label["cases"] and len(rows) == 1 and not apart}
        if apart or selected not in rows:
            record.update(shown=rows.get(selected) or next(iter(rows.values())), claim=None)
            out.append(record)
            record["research"] = research_cell(config, registry, graded, sid, record["shown"]["impl"], label)
            continue
        found = leaderboard.decisions(rows, selected, config.evaluation, history[component], per_case, policy)
        whole = rows[selected]
        record.update(shown=whole, decisions=found, rowset={d.rival: d.other for d in found},
                      claim=found[0].own if found else claim_row(per_case, whole, fraction),
                      stage=deciding_stage(config, registry, sid, whole))
        if fraction:
            top = leaderboard.selection_leader(rows, per_case, fraction, selected, config.evaluation)
            record["leader"] = top or selected
            if record["deciding"] and top and top != selected:
                record["pending"] = top
        else:
            ahead = [d for d in found if d.outcome == "rival" and d.switch]
            if record["deciding"] and ahead:   # a higher rival on all cases that the selected arm was never promoted over
                record["pending"] = leaderboard.rank({d.rival: d.other for d in ahead})[0]["impl"]
        record["research"] = research_cell(config, registry, graded, sid, selected, label)
        out.append(record)
    return out


def result_cell(record: Row) -> str:
    found = record["decisions"]
    text = "; ".join(standing(d, record["rows"]) for d in found) or "no rival measured on the same cases"
    if record["pending"]:
        text += (f"; selection pending: {record['pending']} is highest on the cases that chose it and has no run at the "
                 f"deciding stage ({record['stage'] or 'none'})")
    return text


def rate_cell(record: Row) -> str:
    row = record["claim"] or record["shown"]
    whole = "" if leaderboard.part_of(row) or not record["fraction"] else " (whole set, no held-out split)"
    score = f", balanced score {float(row['balanced']):.4g}" if str(row.get("balanced") or "").strip() else ""
    return evidence_table.rate_label(row) + score + whole


def checks_block(config: Config, registry: Registry, root: Path, today: Optional[datetime.date] = None, compact: bool = False) -> str:
    """The leaderboard table. ``compact`` is the README's: one row per seat, its deciding check only. Otherwise every check that has a
    rival, with the plain-words description, the cases and what public research says."""
    per_case = leaderboard.per_case_rows(config)
    records = [r for r in claims(config, registry, root, today) if not r["conformance"]]
    rate_head = "Held-out pass rate" if leaderboard.holdout_fraction(config) else "Pass rate on all cases"
    if compact:
        records = [r for r in records if r["deciding"] and not r["apart"]]
    head = ["Seat", "Deciding check, stage", "Selected arm", f"{rate_head} (95% interval)", "n", "Cost per passing case", "Median seconds", "Two-sided result against each rival"] if compact \
        else ["Check (solution, part of the mind)", "What it does", "Common-sense check", "Cases and source", "Deciding stage", "Selected arm", f"{rate_head} (95% interval)", "n",
              "Cost per passing case", "Median seconds", "Two-sided result against each rival", "What public research says"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in records:
        row, check = r["claim"] or r["shown"], r["label"]
        if r["apart"]:
            arm, rate = "none: arms are complementary, not ranked", "; ".join(f"{impl} {evidence_table.rate_label(x)}" for impl, x in sorted(r["rows"].items()))
            cost, seconds = "; ".join(f"{impl} {evidence_table.cost_label(x)}" for impl, x in sorted(r["rows"].items())), ""
            result, n = "not ranked: " + check["reason"], ""
        else:
            arm = r["selected"] if r["selected"] in r["rows"] else f"{r['shown']['impl']} (best guess, none selected)"
            rate, n = rate_cell(r), str(row.get("cases", ""))
            cost, seconds = evidence_table.cost_label(r["shown"]), evidence_table.seconds_label(r["shown"], per_case)
            result = result_cell(r)
        stage = (r["stage"] or "no cascade") if r["deciding"] else "not the deciding check"
        if compact:
            cells = [first_cell(r), f"{check['check']} ({stage})", arm, rate, n, cost, seconds, result]
        else:
            cells = [first_cell(r), r["does"], check["check"],
                     check["cases"].replace("{n}", str(r["shown"].get("cases", ""))), stage, arm, rate, n, cost, seconds, result, r["research"]]
        lines.append("| " + " | ".join(evidence_table.cell(c) for c in cells) + " |")
    return "\n".join(lines) if len(lines) > 2 else "No check has a recorded run yet."


def conformance_line(config: Config, registry: Registry, root: Path) -> str:
    """The checks written in this repository that have no rival: they show an arm does its job, not that it beats another."""
    done = []
    for r in claims(config, registry, root):
        if r["conformance"]:
            row = r["shown"]
            done.append(f"{first_cell(r)} {leaderboard.passes(row)}/{row.get('cases')}")
    return "Conformance tests (cases written in this repo, no rival, not counted as alternatives): " + ", ".join(done) + "."


def explain(config: Config) -> str:
    split = leaderboard.holdout_fraction(config)
    cases = (f"Each case set is split by a hash of the case id: {1 - split:.0%} chooses the arm with the highest result at the deciding stage (an exact tie keeps the "
             f"incumbent) and the other {split:.0%} alone gives every rate, interval and test. " if split else
             "The arm with the highest result at the deciding stage on all cases is selected (an exact tie keeps the incumbent), and the same cases give the rate, "
             "interval and test, so each claim is in-sample. ")
    return (cases + "A lead is significant when the two-sided exact McNemar test gives p below 0.05 after Holm's correction across rivals, "
            "with alpha divided by the number of stages the pair was run at; otherwise it is a best guess, not yet significant. "
            "Where a seat's metric is a balanced score, arms are ranked by that score. "
            "Cost per passing case is the whole run's recorded spend over its passes.")


def evidence_block(config: Config, registry: Registry, root: Path, today: Optional[datetime.date] = None) -> str:
    return "\n".join([checks_block(config, registry, root, today, compact=True), "", conformance_line(config, registry, root) + " " + explain(config)
                      + " Every check and every arm: [leaderboard](docs/reference/leaderboard.md), "
                      "[evidence by arm](docs/reference/evidence-by-arm.md)."])


def leaderboard_block(config: Config, registry: Registry, root: Path, today: Optional[datetime.date] = None) -> str:
    """The generated body of docs/reference/leaderboard.md: every check with a rival, then the conformance tests."""
    conformance = [r for r in claims(config, registry, root, today) if r["conformance"]]
    lines = [checks_block(config, registry, root, today), "", "### Conformance tests", "",
             "Cases written in this repository and no rival arm: they show that an arm does its job, and they are not counted as alternatives.", "",
             "| Check | Cases and source | Arm | Pass rate (95% interval) | Cost per passing case |", "|---|---|---|---|---|"]
    for r in conformance:
        lines.append("| " + " | ".join(evidence_table.cell(c) for c in [f"{first_cell(r)}: {r['label']['check']}", r["label"]["cases"].replace("{n}", str(r["shown"].get("cases", ""))),
                                                                              arm_name(registry, r["solution"], r["selected"]), evidence_table.rate_label(r["shown"]), evidence_table.cost_label(r["shown"])]) + " |")
    return "\n".join(lines).replace("](docs/", "](../")   # the page lives in docs/reference/, so root-relative links become relative to it


def arms_block(config: Config, registry: Registry, today: Optional[datetime.date] = None) -> str:
    """Every arm of every recorded component. With a held-out split the rates and tests are the held-out part's; an arm with no per-case
    rows shows its whole set and says so."""
    history = leaderboard.all_results(config.results_path)
    per_case = leaderboard.per_case_rows(config)
    chosen = leaderboard.policies(config, registry, per_case)
    selected_of = leaderboard.selected_impls(config, registry.solutions, registry)
    owner = component_solutions(config, registry)
    try:
        graded = evidence.estimates(evidence.load_for(config), today)
    except evidence.EvidenceError:
        graded = {}
    lines = ["| Component | Arm | Cases (held-out part when split) | Pass rate (95% Wilson) | Cost per passing case | Seconds per case | Versus the selected arm | Public evidence (not in our numbers) |",
             "|---|---|---|---|---|---|---|---|"]
    for component in sorted(history):
        rows = latest_whole(history[component])
        if not rows:
            continue
        selected = selected_of.get(component, "")
        policy = chosen.get(component) or leaderboard.Policy()
        apart = bool(leaderboard.invariant_reason(component, config.evaluation))
        found = {d.rival: d for d in leaderboard.decisions(rows, selected, config.evaluation, history[component], per_case, policy)} \
            if selected in rows and not apart else {}
        for impl in sorted(rows, key=lambda i: (i != selected, i)):
            row = rows[impl]
            shown = claim_row(per_case, row, policy.holdout)
            if apart:
                versus = "complementary arm, not ranked"
            elif impl == selected:
                versus = "selected"
            elif impl in found:
                versus = standing(found[impl], rows)
            else:
                versus = "not compared: no run on the same cases as the selected arm"
            cells = [component, impl + (" (selected)" if impl == selected else ""), str(shown.get("cases", "")), evidence_table.rate_label(shown),
                     evidence_table.cost_label(row), evidence_table.seconds_label(row, per_case), versus,
                     evidence_table.public_label(config, registry, graded, owner.get(component, ""), impl)]
            lines.append("| " + " | ".join(evidence_table.cell(c) for c in cells) + " |")
    return "\n".join(lines)


def first_cell(row: Row) -> str:
    """The first cell of a check row: the solution's display name, its part of the mind when that differs, then its id as the call handle."""
    name = row.get("display") or ""
    shown = ", ".join(x for x in (name, row["seat"] if row["seat"] != name else "") if x)
    handle = f"`{row['solution'] or row['component']}`"
    return f"{shown} ({handle})" if shown else handle


#: The parts of the mind as Joshua approved them: five containers, each holding its second-level parts, with the parts nested under them. Each
#: entry is ``(solution id, the id of the part it is inside, or "" for a container)``. Names, counts and descriptions come from the records.
MIND_TREE = (
    ("the-self", ""),
    ("system-integrity", "the-self"), ("role-understanding", "the-self"), ("the-assembler", "the-self"),
    ("the-body", ""),
    ("internal-context", "the-body"), ("card-store", "internal-context"), ("intake-sources", "the-body"),
    ("the-hands", "the-body"),
    ("the-intelligence", ""),
    ("the-mind", "the-intelligence"), ("context-intake", "the-mind"), ("planner", "the-mind"),
    ("delegation", "the-mind"), ("response-writer", "the-mind"), ("route-a-request", "the-mind"), ("resolve-a-reference", "the-mind"),
    ("higher-mind", "the-intelligence"), ("long-term-memory", "higher-mind"), ("live-objectives", "higher-mind"), ("guidance", "higher-mind"),
    ("the-subconscious", "the-intelligence"), ("the-intuition", "the-subconscious"), ("cards-from-files", "the-subconscious"),
    ("context-retriever", "the-subconscious"),
    ("critical-thinking", "the-intelligence"), ("esoi-application", "critical-thinking"), ("metric-translation", "critical-thinking"),
    ("goal-completion", "critical-thinking"), ("response-quality", "critical-thinking"), ("decision-check", "critical-thinking"),
    ("nervous-system", "the-intelligence"), ("proactivity", "the-intelligence"),
    ("the-world", ""),
    ("the-science", "the-world"),
    ("the-tools", "the-world"), ("web-search", "the-tools"), ("read-files", "the-tools"), ("file-editing", "the-tools"),
    ("connected-system-operations", "the-tools"), ("delegated-agent-sessions", "the-tools"),
    ("model-plumbing", "the-world"), ("model-tier-chooser", "model-plumbing"), ("vendor-model-caller", "model-plumbing"),
    ("the-learning", "the-world"), ("research-freshness-reader", "the-learning"),
    ("the-consciousness", ""),
    ("the-representatives", "the-consciousness"), ("judgment-calls", "the-consciousness"), ("feedback-learning", "the-consciousness"),
    ("prioritization", "the-consciousness"), ("request-intake", "the-consciousness"), ("terminal-session", "the-consciousness"),
)
#: A solution with one of these ids is a mind seat, and its name is the part's name.
MIND_SEATS = tuple(sid for sid, _inside in MIND_TREE)


def arm_name(registry: Registry, solution_id: str, arm: str) -> str:
    """An arm's human name with its id as the handle, from the implementation records; the id alone when no record names it."""
    for row in registry.implementations:
        if row.get("solution_id") == solution_id and row.get("implementation_id", "").split(":")[-1] == arm and row.get("name"):
            return f"{row['name']} (`{arm}`)"
    return f"`{arm}`" if arm else ""


def mind_part(sol: Dict[str, str]) -> str:
    """The part of the mind a solution is, which is its display name, or "" when it is not a mind seat."""
    return sol.get("name", "") if sol.get("solution_id") in MIND_SEATS else ""


def unmeasured_block(config: Config, registry: Registry, root: Path) -> str:
    """What is named but has no run: mind seats with no measured solution, and arms a metric names that have no recorded row."""
    history = leaderboard.all_results(config.results_path)
    reasons = {x["key"]: x["reason"] for x in labels(root) if x["kind"] == "gap"}
    waived = {w["path"]: w["reason"] for w in registry.waivers if w.get("rule") == "S24"}   # a waiver already says why an arm has no run
    measured_seats = {x["seat"] for x in labels(root) if x["kind"] == "check" and x["key"] in history}
    lines = []
    seats = {sol["solution_id"]: sol for sol in registry.every_solution()}
    empty = []
    tree = dict(MIND_TREE)
    for sid in MIND_SEATS:
        sol = seats.get(sid)
        part = mind_part(sol) if sol else ""
        if not part:
            continue
        if not sol.get("interface_name") or not sol.get("implementations"):
            empty.append(part)      # a seat defined and empty: it has no arm (its interface may be declared) and no check yet
            continue
        top = not tree[sid] or not tree[tree[sid]]      # a container or a second-level part; the parts nested under them are listed through their arms
        if not top or (not tree[sid] and sid not in reasons and f"{sid}:rest" not in reasons):
            continue
        if sid not in measured_seats:
            why = reasons.get(sid, "no check is written yet")
            lines.append(f"- **{part}** (`{sid}`): not measured. {why}")
        elif f"{sid}:rest" in reasons:
            lines.append(f"- **{part}** (`{sid}`): measured in part. {reasons[sid + ':rest']}")
    if empty:
        lines.append(f"- **Seats defined and empty**, with no arm and no check yet: {', '.join(empty)}.")
    grouped: Dict[tuple, List[str]] = {}
    for sol in registry.solutions:
        for component, impl in harness_arms(config, sol.get("metric_command", "")):
            if impl not in history.get(component, {}):
                why = reasons.get(f"{component}:{impl}") or reasons.get(component) or waived.get(f"{sol['solution_id']}:{impl}") or "No run is recorded yet."
                grouped.setdefault((sol["solution_id"], why), []).append(arm_name(registry, sol["solution_id"], impl) + (f" ({component})" if component != sol["solution_id"].replace("-", "_") else ""))
    named = {x["solution_id"]: x.get("name", "") for x in registry.every_solution()}
    for (sid, why), arms in grouped.items():
        lines.append(f"- **{named.get(sid) or sid}** (`{sid}`), arms with no run: {', '.join(dict.fromkeys(arms))}. {why}")
    return "\n".join(lines) or "Every named seat and arm has a recorded run."


def counted_arms(config: Config, root: Path) -> Dict[str, List[str]]:
    """``{area: [arm, ...]}``: the distinct real alternatives with a recorded whole run, by the area label of their check
    (``docs/reference/evidence-labels.csv``). Left out: a check with no area label (mechanics such as the single-scenario assembly), and any arm
    that marks itself an ablation or validity reference in its module docstring. Diagnostic bounds (``none``, ``single_provider``) are ranked alternatives and counted."""
    history = leaderboard.all_results(config.results_path)
    out: Dict[str, List[str]] = {}
    for label in labels(root):
        area = label.get("area", "")
        if label["kind"] != "check" or not area or label["key"] not in history:
            continue
        whole = latest_whole(history[label["key"]])
        if "(this repo)" in label["cases"] and len(whole) == 1:   # a conformance test: no rival, so no alternative
            continue
        for impl, row in whole.items():
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
    lines += ["", seat_sentence(config, registry, root) + " Counted: distinct arms with a recorded run on the same cases as their rivals. Diagnostic bounds (such as `none` and `single_provider`) are counted, "
              "because they are ranked on the same number as every arm; conformance tests, which have no rival, are not ([how we measure](docs/explanation/how-we-measure.md#what-counts-as-an-alternative))."]
    return "\n".join(lines)


def seat_sentence(config: Config, registry: Registry, root: Path) -> str:
    """What the evidence table shows about the selections, computed from the same records: how many seats with a rival hold the arm
    that is highest on the cases that chose it, and how the held-out cases read for them."""
    seats = [r for r in claims(config, registry, root) if r["deciding"] and not r["apart"] and not r["conformance"] and r["decisions"]]
    if not seats:
        return "No seat has a rival measured on the same cases yet."
    chosen = [r for r in seats if not r["pending"]]
    pending = [r for r in seats if r["pending"]]
    behind = [r for r in seats if any(d.outcome == "rival" for d in r["decisions"])]
    significant = [r for r in seats if any(d.outcome == "rival" and d.significant for d in r["decisions"])]
    fraction = seats[0]["fraction"]
    scope = "on the cases that chose it" if fraction else "on all cases at the deciding stage"
    text = (f"Of {len(seats)} seats with rival arms on the same cases, {len(chosen)} hold the arm with the highest result {scope}"
            + (f"; for {', '.join('`' + r['solution'] + '`' for r in pending)} a rival is highest and has no run at the deciding stage yet" if pending else "")
            + ".")
    if fraction:
        text += (f" On the {fraction:.0%} of cases held out from the choice, {len(behind)} of {len(seats)} selected arms have a rival ahead and "
                 f"{len(significant)} of those leads {'is' if len(significant) == 1 else 'are'} significant (two-sided).")
    else:
        text += (f" The claims are in-sample (the same cases chose the arm and report it): {len(significant)} of {len(seats)} selected arms are significantly "
                 "ahead of every rival, two-sided.")
    return text


def compact_headline(config: Config, root: Path) -> str:
    """The headline as one paragraph for a post or an article: the totals, then the count per area."""
    areas = counted_arms(config, root)
    candidates = len(read_csv(root / "hubofhubs" / "registry" / "hub_findings.csv"))
    per_area = ", ".join(f"{area} {len(arms)}" for area, arms in areas.items())
    return f"{sum(len(a) for a in areas.values())} alternatives measured across {len(areas)} areas, from {candidates} researched candidates. By area: {per_area}."
