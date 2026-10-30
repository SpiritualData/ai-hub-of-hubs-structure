"""Renders generated blocks between markers, in place and never appended (the idea of ``esoi check --write-docs``).

``seat_table`` states facts from the registry: area, seat, hubs a consumer builds on, candidates, last researched.
``metric_lines`` states a consumer's reading, from its ``Binding``. ``rewrite`` swaps the text between a begin and an end
marker; ``--check`` style use compares the result with the file."""
import re

from . import registry

STATUS_BEGIN, STATUS_END = "<!-- seats:start -->", "<!-- seats:end -->"
DETAIL_BEGIN, DETAIL_END = "<!-- registry:start -->", "<!-- registry:end -->"


def names(cell):
    return ", ".join(n for n, _url, _lic in registry.parse_hubs(cell)) or "none"


def seat_table(folder=None, facts=None, areas=None):
    """A markdown table of areas. With ``facts`` (from a consumer) it adds what the consumer hand-wires and whether research is
    fresh. With ``areas`` (a collection of area names) it lists only those."""
    head = ["Area", "Seat", "Built on", "Candidates", "Researched"]
    if facts:
        head += ["Freshness", "Hand-wired where a hub covers it"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for row in registry.read("hubs.csv", folder):
        if areas is not None and row["area"] not in areas:
            continue
        cells = [row["area"], row["seat"], names(row["current_hubs"]), "; ".join(registry.split(row["candidate_hubs"])),
                 row["last_researched"]]
        if facts:
            f = facts[row["area"]]
            cells += ["fresh" if f["fresh"] else "STALE", ", ".join(f["reinvented"]) or "none"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def seat_summary(folder=None, seats=None, link="docs/registry.md"):
    """One row per seat with its area count, so the table stays the size of the mind and not of the registry. ``seats`` is the
    ordered list of ``(seat id, part of the mind)``; a seat with no researched area shows 0. Without it, the seats of the
    registry in order of first appearance."""
    hubs = registry.read("hubs.csv", folder)
    findings = registry.read("hub_findings.csv", folder)
    seats = seats or [(s, s) for s in dict.fromkeys(r["seat"] for r in hubs)]
    lines = ["| Seat | Part of the mind | Areas | Built on now | Candidates researched | Oldest research |", "|---|---|---|---|---|---|"]
    for seat, part in seats:
        mine = [r for r in hubs if r["seat"] == seat]
        found = sum(len(registry.findings_of(r, findings)) for r in mine)
        built = sum(1 for r in mine if registry.parse_hubs(r["current_hubs"]))
        oldest = min((r["last_researched"] for r in mine), default="none")
        lines.append(f"| {seat} | {part} | {len(mine)} | {built} | {found} | {oldest} |")
    lines.append(f"\n{len(hubs)} areas and {len(findings)} researched candidates in all; every area is listed in [{link}]({link}).")
    return "\n".join(lines)


def area_detail(folder=None, seats=None):
    """Every area, grouped by seat, with its candidates and the evidence count: the generated body of ``docs/registry.md``."""
    hubs = registry.read("hubs.csv", folder)
    findings = registry.read("hub_findings.csv", folder)
    seats = seats or [(s, s) for s in dict.fromkeys(r["seat"] for r in hubs)]
    out = []
    for seat, part in seats:
        mine = [r for r in hubs if r["seat"] == seat]
        if not mine:
            continue
        out += [f"### {seat} ({part})", "", "| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |", "|---|---|---|---|---|---|---|---|"]
        for r in mine:
            out.append("| " + " | ".join([r["area"], r["serves"], r["status"], r.get("call") or "-", names(r["current_hubs"]),
                                          "; ".join(registry.split(r["candidate_hubs"])) or "none",
                                          str(len(registry.findings_of(r, findings))), r["last_researched"]]) + " |")
        out.append("")
    return "\n".join(out).rstrip()


def metric_lines(m, facts):
    stale = [a for a, f in facts.items() if not f["fresh"]]
    return "\n".join([
        f"- coverage (areas with a hub or a recorded decision): {m['coverage']:.2f}",
        f"- integration by configuration (share of wired hub connections that need no code): {m['config_share']:.2f}",
        f"- research freshness: share of areas researched within {registry.STALENESS_DAYS} days {m['fresh_share']:.2f}; "
        f"stale: {', '.join(stale) or 'none'}",
        f"- reinvented integrations (single services hand-wired where a hub covers them, no waiver): {m['reinvented']} "
        f"({m['waived']} more waived with a reason); areas free of them {m['reinvented_free_share']:.2f}",
        f"- code: of the {m.get('to_connect', len(facts))} areas whose call is adopt or coexist, share with one seam {m['seam_share']:.2f} "
        f"and selectable by metric {m['selectable_share']:.2f}; vendor branches in core {m['vendor_branches']}",
        f"- real gaps (call adopt or coexist, no seam): {', '.join(m.get('unconnected') or []) or 'none'}",
        f"- score: {m['score']:.3f}"])


def rewrite(text, begin, end, block):
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise ValueError(f"no generated block between {begin} and {end}")
    return pattern.sub(lambda _m: f"{begin}\n{block}\n{end}", text)
