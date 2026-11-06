"""Rebuild cases.json for Hands: a written declaration of a system's enduring integrations and the run records of a recent period, with what a careful reader
reports for each integration (reachable, used, or declared but unused). Eight cases: integrations that are used, declared but idle, cut off (no tool or disabled),
two systems in one declaration, a system that declares nothing, and a run record that names an integration nobody declared (which is not reported).

    python3 evaluation/hands/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def row(name, kind, reachable, used):
    return {"name": name, "kind": kind, "reachable": reachable, "used": used, "unused": reachable and not used}


def main():
    registry = {"name": "tool-registry", "kind": "tool_registry", "system": "s1", "tool": "list_tools"}
    platform = {"name": "model-platform", "kind": "llm_platform", "system": "s1", "tool": "complete"}
    guard = {"name": "guardrails", "kind": "guardrails", "system": "s1", "tool": "check"}
    broken = {"name": "ticketing", "kind": "tool_registry", "system": "s1"}
    off = {"name": "search", "kind": "tool_registry", "system": "s1", "tool": "find", "disabled": True}
    other = {"name": "mailer", "kind": "tool_registry", "system": "s2", "tool": "send"}
    cases = []
    for name, system, declared, runs, expect in (
            ("all-used", "s1", [registry, platform], [{"used": ["tool-registry", "model-platform"]}], [row("tool-registry", "tool_registry", True, True), row("model-platform", "llm_platform", True, True)]),
            ("one-idle", "s1", [registry, guard], [{"used": ["tool-registry"]}], [row("tool-registry", "tool_registry", True, True), row("guardrails", "guardrails", True, False)]),
            ("none-used", "s1", [platform], [], [row("model-platform", "llm_platform", True, False)]),
            ("no-tool-named", "s1", [broken], [{"used": ["ticketing"]}], [row("ticketing", "tool_registry", False, True)]),
            ("disabled", "s1", [off], [], [row("search", "tool_registry", False, False)]),
            ("two-systems-asks-one", "s2", [registry, other], [{"used": ["mailer"]}], [row("mailer", "tool_registry", True, True)]),
            ("declares-nothing", "s3", [registry], [{"used": ["tool-registry"]}], []),
            ("undeclared-use-not-reported", "s1", [registry], [{"used": ["tool-registry", "mystery"]}], [row("tool-registry", "tool_registry", True, True)])):
        cases.append({"id": "hands-" + name, "kind": "unused" if "idle" in name or "none-used" in name else "reach" if name in ("no-tool-named", "disabled") else "declared",
                      "args": {"system": system, "declared": declared, "runs": runs}, "expect": expect})
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
