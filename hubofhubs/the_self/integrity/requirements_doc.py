"""The generated reference of what every arm needs, read from the arms' ``REQUIRES`` declarations (``hubofhubs/the_self/assembler/arm_needs.py``).

Nothing here is typed by hand: ``requirements_block`` walks every declared arm of the hub and renders two tables, one row per arm
and one row per external service, between the markers of ``docs/reference/requirements-by-arm.md`` (``scripts/status.py``). A
variable's value is never read or printed. ``env_example`` renders the ``.env.example`` of the default assembly the way
``esoi requirements --package hubofhubs --env-template .env.example`` does.
"""
from pathlib import Path
from typing import Dict, List

from esoi import requirements as needs
from esoi import AssemblyConfig

from hubofhubs.the_self.assembler.resolution import assembler

BEGIN, END = "<!-- requirements:start -->", "<!-- requirements:end -->"


def members(every_arm: bool = True):
    """The closure of the hub's assembly: every declared arm when ``every_arm``, else the arms a default assembly uses."""
    return assembler().closure(AssemblyConfig(), None, (), every_arm)


def entries(every_arm: bool = False) -> List[needs.Entry]:
    return needs.gather(needs.members_pairs(members(every_arm)))


def link(text: str, url: str) -> str:
    return f"[{text}]({url})" if url else ""


def arm_cells(items) -> Dict[str, List[str]]:
    cells: Dict[str, List[str]] = {"env": [], "api": [], "python": [], "other": [], "out": []}
    for item in items:
        flag = "" if item.required else " (optional)"
        if isinstance(item, needs.Env):
            cells["env"].append("`" + "` or `".join(item.names) + "`" + (" (secret)" if item.secret else "") + flag)
        elif isinstance(item, needs.Api):
            key = (" (`" + "` or `".join(item.key.names) + "`)") if item.key else ""
            cells["api"].append(item.service + key + (", keyless works" if item.keyless else "") + flag)
        elif isinstance(item, needs.Python):
            cells["python"].append(f"`{item.module}` via extra `{item.extra}`" + flag if item.extra else f"`{item.module}`" + flag)
        elif isinstance(item, needs.Binary):
            cells["other"].append(f"program `{item.name}`" + flag)
        elif isinstance(item, needs.Service):
            cells["other"].append(f"service {item.name} (`{item.url_env}`" + (f", default {item.default_url}" if item.default_url else "") + ")" + flag)
        elif isinstance(item, needs.Download):
            cells["other"].append(f"download {item.name}" + (f", {item.size_mb:g} MB" if item.size_mb else "") + flag)
        elif isinstance(item, needs.Isolate):
            cells["out"].append(item.boundary)
        elif isinstance(item, needs.Resource):
            cells["other"].append("account note: " + item.note)
    return cells


def arm_names() -> Dict[str, str]:
    """``{solution id:arm: "Part name, Arm name"}`` from the records of a checkout, so the table is read by names; empty in an installed package."""
    from esoi import read_tree
    root = Path(__file__).resolve().parents[3] / "esoi"
    try:
        parts = {r["solution_id"]: r["name"] for r in read_tree(root, "solutions.csv")}
        arms = read_tree(root, "implementations.csv")
    except (OSError, KeyError, ValueError):
        return {}
    return {r["implementation_id"]: ", ".join(x for x in (parts.get(r["solution_id"], ""), r.get("name", "")) if x) for r in arms}


def arm_table() -> str:
    names = arm_names()
    head = ["Part and arm", "Environment variables", "Accounts and APIs", "Python (extra of `hubofhubs`)", "Programs, services, downloads", "Can run out of process"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for member in sorted(members(), key=lambda m: m.label):
        own = [item for item in needs.declared(member.target)]
        cells = arm_cells(own)
        row = [f"{names[member.label]} (`{member.label}`)" if names.get(member.label) else f"`{member.label}`"] + ["<br>".join(cells[key]) or "none" for key in ("env", "api", "python", "other")] + [", ".join(cells["out"]) or "no"]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def service_table() -> str:
    head = ["Service", "Key variable", "Without a key", "Free tier", "Rate limit", "Links", "As of"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    seen = {}
    for member in members():
        for item in needs.declared(member.target):
            if isinstance(item, needs.Api) and item.service not in seen:
                seen[item.service] = item
    for name in sorted(seen):
        item = seen[name]
        key = ("`" + "` or `".join(item.key.names) + "`") if item.key else "see the arm's variables"
        links = ", ".join(x for x in (link("sign up", item.signup_url), link("docs", item.docs_url), link("pricing", item.pricing_url)) if x) or "none"
        row = [item.service, key, "works" if item.keyless else "needs the key", item.free_tier or "not stated here", item.rate_limit or "not stated here", links, item.as_of or "undated"]
        lines.append("| " + " | ".join(cell.replace("|", "/") for cell in row) + " |")
    return "\n".join(lines)


def requirements_block() -> str:
    return "\n".join(["### Per arm", "", arm_table(), "", "### External services and accounts", "", service_table()])


def env_example() -> str:
    """The ``.env.example`` for the default assembly (no values)."""
    return needs.env_template(entries(False))
