"""Renders generated blocks between markers, in place and never appended (the idea of ``esoi check --write-docs``).

``seat_table`` states facts from the registry: area, seat, hubs a consumer builds on, candidates, last researched.
``metric_lines`` states a consumer's reading, from its ``Binding``. ``rewrite`` swaps the text between a begin and an end
marker; ``--check`` style use compares the result with the file."""
import re

from . import registry

STATUS_BEGIN, STATUS_END = "<!-- seats:start -->", "<!-- seats:end -->"


def names(cell):
    return ", ".join(n for n, _url, _lic in registry.parse_hubs(cell)) or "none"


def seat_table(folder=None, facts=None):
    """A markdown table. With ``facts`` (from a consumer) it adds what the consumer hand-wires and whether research is fresh."""
    head = ["Area", "Seat", "Built on", "Candidates", "Researched"]
    if facts:
        head += ["Freshness", "Hand-wired where a hub covers it"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for row in registry.read("hubs.csv", folder):
        cells = [row["area"], row["seat"], names(row["current_hubs"]), "; ".join(registry.split(row["candidate_hubs"])),
                 row["last_researched"]]
        if facts:
            f = facts[row["area"]]
            cells += ["fresh" if f["fresh"] else "STALE", ", ".join(f["reinvented"]) or "none"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def metric_lines(m, facts):
    stale = [a for a, f in facts.items() if not f["fresh"]]
    return "\n".join([
        f"- coverage (areas with a hub or a recorded decision): {m['coverage']:.2f}",
        f"- integration by configuration (share of wired hub connections that need no code): {m['config_share']:.2f}",
        f"- research freshness: share of areas researched within {registry.STALENESS_DAYS} days {m['fresh_share']:.2f}; "
        f"stale: {', '.join(stale) or 'none'}",
        f"- reinvented integrations (single services hand-wired where a hub covers them, no waiver): {m['reinvented']} "
        f"({m['waived']} more waived with a reason); areas free of them {m['reinvented_free_share']:.2f}",
        f"- code: areas with one seam {m['seam_share']:.2f}, selectable by metric {m['selectable_share']:.2f}, "
        f"vendor branches in core {m['vendor_branches']}",
        f"- score: {m['score']:.3f}"])


def rewrite(text, begin, end, block):
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise ValueError(f"no generated block between {begin} and {end}")
    return pattern.sub(lambda _m: f"{begin}\n{block}\n{end}", text)
