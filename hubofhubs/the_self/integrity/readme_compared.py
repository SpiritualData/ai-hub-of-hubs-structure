"""The two generated blocks of the top README: the size of the structure and the alternatives compared in the areas people ask about most.

Everything here is read from the records and from ``esoi/results.csv`` (``scripts/status.py`` rewrites the blocks), so the README cannot claim a
count or a score the records do not hold. A table ranks the alternatives of one area on the newest run of each, best first (the metric's own
order: pass rate or balanced score, then cost), and keeps only the runs on the cases most alternatives share so the rows are comparable.
"""
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

from esoi.optimization.leaderboard import ranking, results_log
from esoi.structure.intent_registry.registry import Registry

COUNTS_BEGIN, COUNTS_END = "<!-- counts:start -->", "<!-- counts:end -->"
COMPARED_BEGIN, COMPARED_END = "<!-- compared:start -->", "<!-- compared:end -->"
TOP = 3

#: (heading, what people use it for, results component, solution id whose selected arm is marked, note on how to read the score)
AREAS: List[Tuple[str, str, str, str, str]] = [
    ("AI harnesses", "The loop that carries out a long task: Claude Code, opencode, the hub's own loops.", "agent_sessions_hard", "delegated-agent-sessions",
     "Hard tasks finished, with their cost and time in the score."),
    ("Terminal UIs", "The screen a person works in: how a session is drawn and steered.", "terminal_presentation", "terminal-session",
     "Scripted terminal sessions drawn and steered right, then how readable the screen is."),
    ("Context management: finding the right files", "The Subconscious picks what a request needs from the files, cards and memory.", "context_retrieval", "context-retriever",
     "The needed text is among what is shown within a token budget, with little noise."),
    ("Context management: cards built from files", "The cards that let the Subconscious recall a folder.", "cards_from_files", "cards-from-files",
     "The file a task needs is among the first three a builder's cards show."),
    ("Models for the tiers: the fast tier", "Which model does the fast roles (classification, choosing files) as well as the tier above.", "fast_roles_pool", "model-tier-chooser",
     "The pooled cases of the fast roles, with cost in the score."),
    ("Models for the tiers: hard reasoning", "How current models do exact-answer competition maths, one prompt for all.", "model_quality_aime", "model-tier-chooser",
     "Problems with the right final answer."),
]


def label(registry: Registry, impl: str) -> str:
    base, _, settings = impl.partition("@")
    for row in registry.implementations:
        if row.get("implementation_id", "").split(":", 1)[-1] == base and row.get("name", "").strip():
            name = " ".join(row["name"].split())
            return f"{name} ({settings.replace(',', ', ')})" if settings else name
    return f"`{base}`" + (f" ({settings.replace(',', ', ')})" if settings else "")


def table(registry: Registry, rows: Dict[str, Dict[str, str]], picked: str) -> List[str]:
    ranked = ranking.rank(rows)
    groups: Dict[str, List[Dict[str, str]]] = {}
    for r in ranked:
        groups.setdefault(r.get("cases_sha", ""), []).append(r)
    same = max(groups.values(), key=lambda g: (len(g), max(x.get("date", "") for x in g)))   # the cases most alternatives were run on
    full = max(int(float(r.get("cases") or 0)) for r in same)
    same = [r for r in same if int(float(r.get("cases") or 0)) == full]   # a run on fewer cases is not comparable
    shown = same[:TOP]
    places = list(range(1, len(shown) + 1))
    for place, r in enumerate(same, 1):   # the alternative in use is always shown, at its own place, even when it ranks below the top rows
        if place > TOP and picked and r["impl"].split("@")[0] == picked.split("@")[0]:
            shown, places = shown + [r], places + [place]
            break
    models = any((r.get("model") or "none") not in ("none", "") for r in shown)
    head = ["#", "Alternative"] + (["Model"] if models else []) + ["Result", "Cost per case", "In use"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for place, r in zip(places, shown):
        cases = int(float(r.get("cases") or 0))
        score = f"score {ranking.pass_rate(r):.2f}" if str(r.get("balanced") or "").strip() else f"{round(100 * ranking.pass_rate(r))}%"
        cost = "-" if not ranking.cost_known(r) else "free" if float(r["cost_usd"]) == 0 else f"${float(r['cost_usd']) / max(cases, 1):.4f}"
        used = "selected" if picked and r["impl"].split("@")[0] == picked.split("@")[0] else ""
        cells = [str(place), label(registry, r["impl"])] + ([r.get("model") or "-"] if models else []) + [f"{score}, {ranking.passes(r)} of {cases} cases", cost, used]
        lines.append("| " + " | ".join(cells) + " |")
    return lines + [f"", f"{len(same)} compared on the same {int(float(same[0].get('cases') or 0))} cases; latest run {max(r.get('date', '') for r in same)}."]


def counts_block(registry: Registry) -> str:
    solutions = registry.every_solution()
    chosen = sum(1 for s in solutions if (s.get("selected") or "").strip())
    return (f"**{len(solutions)} solutions** in the full hierarchy, with **{len(registry.implementations)} alternative implementations** "
            f"and **{len(registry.metrics)} metrics**; {chosen} of the solutions have an implementation selected, and where rivals have been measured the selection follows the metric.")


#: The tracker's verdict on a solution's selection, in plain words.
VERDICT_WORDS = {"WIN": "the metric's leader won by a significant margin", "TIE": "kept on a tie: on the cases that decide it, the leader's margin is not significant and this one costs less",
                 "UNMEASURED": "no rival has been measured on the same cases yet"}


def verdicts(config) -> Dict[str, Tuple[str, str]]:
    """The tracker's verdict and its detail per solution id (empty when the tracker has not been generated)."""
    path = Path(config.tracker_dir) / "solutions.csv"
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        return {r["solution_id"]: ((r.get("verdict") or "").strip(), " ".join((r.get("verdict_detail") or "").split())) for r in csv.DictReader(handle)}


def in_use_line(registry: Registry, solution: Dict[str, str], verdict: Tuple[str, str], rows: Dict[str, Dict[str, str]]) -> str:
    """One sentence that says which alternative is in use and why, only when the top row is not the one in use, so such a table explains itself."""
    picked = (solution.get("selected") or "").strip()
    if not picked:
        return ""
    if not any(r["impl"].split("@")[0] == picked.split("@")[0] for r in rows.values()):
        name = " ".join((solution.get("name") or solution.get("solution_id", "")).split())
        return f"In use: none of these rows directly; {name} picks among them by its own metric, and these rows are the hub's own check of the candidates."
    ranked = ranking.rank(rows)
    if ranked and ranked[0]["impl"].split("@")[0] == picked.split("@")[0]:
        return ""   # the top row is the one in use: the table already says so
    status, detail = verdict
    for impl in sorted({r["impl"] for r in rows.values()}, key=len, reverse=True):   # raw arm ids in the tracker's detail read as their names
        detail = detail.replace(impl, label(registry, impl))
    tie = re.search(r"lead (\d+)/(\d+) vs (\d+)/(\d+)", detail) if status == "TIE" else None
    if tie:
        return (f"In use: {label(registry, picked)}. On the {tie.group(2)} pooled cases that decide it, the leader passed {tie.group(1)} and this one "
                f"{tie.group(3)}, a gap that is not significant, and this one costs less per case, so it stays until a rival wins clearly.")
    why = VERDICT_WORDS.get(status, "")
    return f"In use: {label(registry, picked)}" + (f"; {why} ({detail})." if why and detail else f"; {why}." if why else ".")


def compared_block(config, registry: Registry) -> str:
    results = results_log.latest_results(config.results_path)
    solutions = {s.get("solution_id", ""): s for s in registry.every_solution()}
    decided = verdicts(config)
    out: List[str] = []
    for heading, what, component, solution, how in AREAS:
        rows = results.get(component, {})
        if not rows:
            continue
        record = solutions.get(solution, {})
        line = in_use_line(registry, record, decided.get(solution, ("", "")), rows)
        out += [f"#### {heading}", "", f"{what} Score: {how}", ""] + table(registry, rows, (record.get("selected") or "").strip()) + (["", line] if line else []) + [""]
    return "\n".join(out).rstrip()
