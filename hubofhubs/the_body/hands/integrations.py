"""Hands: reports a system's enduring integrations, each with whether the AI can reach it and whether the recent runs used it. The declaration and the
run records are the system's own, handed in; nothing is called. Standard library plus ``esoi``."""
from typing import Any, Dict, Mapping, Optional, Sequence

from esoi import implementation


def declared_for(declared: Sequence[Mapping[str, Any]], system: str) -> Sequence[Mapping[str, Any]]:
    return [d for d in declared if not system or str(d.get("system") or "") == system]


@implementation("the-hands", "declared_and_used")
class DeclaredAndUsed:
    """Lists each declared integration of the system with ``reachable`` (it names a ``tool`` the AI can call and is not marked ``disabled``) and ``used`` (a
    recent run record lists it in ``used``), and marks the ones declared but never used so they are reported rather than forgotten."""
    REQUIRES = ()     # the declaration and the run records are constructor arguments

    def __init__(self, declared: Sequence[Mapping[str, Any]] = (), runs: Sequence[Mapping[str, Any]] = ()):
        self.declared, self.runs = list(declared), list(runs)

    def integrations(self, system: str = "") -> Sequence[Mapping[str, Any]]:
        used = {str(name) for run in self.runs for name in (run.get("used") or [])}
        rows = []
        for d in declared_for(self.declared, system):
            name = str(d.get("name") or "")
            reachable = bool(str(d.get("tool") or "").strip()) and not d.get("disabled")
            rows.append({"name": name, "kind": str(d.get("kind") or ""), "reachable": reachable, "used": name in used, "unused": reachable and name not in used})
        return rows


@implementation("the-hands", "declaration_only")
class DeclarationOnly:
    """Lists the declared integrations as the declaration gives them and checks neither reach nor use: a list a registry can print, which cannot say that a
    declared integration is idle or cut off."""
    REQUIRES = ()     # the declaration is a constructor argument

    def __init__(self, declared: Sequence[Mapping[str, Any]] = (), runs: Sequence[Mapping[str, Any]] = ()):
        self.declared = list(declared)

    def integrations(self, system: str = "") -> Sequence[Mapping[str, Any]]:
        return [{"name": str(d.get("name") or ""), "kind": str(d.get("kind") or ""), "reachable": True, "used": True, "unused": False}
                for d in declared_for(self.declared, system)]
