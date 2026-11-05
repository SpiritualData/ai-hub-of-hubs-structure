"""Role Understanding: states the role of a part (what it is for, what it is not responsible for, who owns that) from the hub's own records, so a part and
the Assembler read the same words. ``RecordedRole`` reads the role fields of the solution's row; ``CheckedRole`` also checks the role against the calls the
part's code actually makes and reports each contradiction. Standard library plus the hub and ``esoi``; nothing is made up for a field the records leave empty."""
import ast
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation, read_tree, split_ids

import hubofhubs

ROLE_FIELDS = ("purpose", "out_of_scope")
UNKNOWN_OWNER, SELF_OWNER, UNDECLARED_CALL = "unknown-owner", "self-owner", "undeclared-call"


def records_folder() -> Path:
    """The hub's structure folder, the one ``esoi.toml`` lists the records beside the code from."""
    return Path(hubofhubs.__file__).resolve().parent.parent / "esoi"


def calls_in(text: str) -> List[str]:
    """The solution ids that source text calls through ``take(part, "<id>", ...)``: the literal second argument of each call, in order."""
    found: List[str] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "take" and len(node.args) > 1:
            second = node.args[1]
            if isinstance(second, ast.Constant) and isinstance(second.value, str) and second.value not in found:
                found.append(second.value)
    return found


@implementation("role-understanding", "recorded_role")
class RecordedRole:
    """The role of a part as its row in ``solutions.csv`` states it: purpose, out of scope and the owners named in ``delegates_to``. A part the records
    do not know is ``stated: False``, and an empty field stays empty. It says nothing of contradictions: the bound the checking arm has to beat."""
    REQUIRES = ()     # reads the records folder it is given

    def __init__(self, solutions: Optional[Sequence[Mapping[str, str]]] = None, implementations: Optional[Sequence[Mapping[str, str]]] = None,
                 code: Optional[Mapping[str, str]] = None, folder: Optional[Path] = None):
        folder = folder or records_folder()
        self.solutions = {r["solution_id"]: r for r in (solutions if solutions is not None else read_tree(folder, "solutions.csv"))}
        self.implementations = list(implementations if implementations is not None else read_tree(folder, "implementations.csv"))
        self.code = code

    def source(self, filepath: str) -> str:
        if self.code is not None:
            return self.code.get(filepath, "")
        path = Path(hubofhubs.__file__).resolve().parent.parent / filepath
        return path.read_text() if filepath and path.is_file() else ""

    def state_role(self, part_id: str) -> Mapping[str, Any]:
        row = self.solutions.get(part_id)
        if row is None:
            return {"part": part_id, "stated": False}
        role: Dict[str, Any] = {"part": part_id, "stated": True, **{field: (row.get(field) or "").strip() for field in ROLE_FIELDS}}
        role["delegates_to"] = [owner for owner in split_ids(row.get("delegates_to", "")) if owner != "none"]
        return role


@implementation("role-understanding", "checked_role")
class CheckedRole(RecordedRole):
    """The recorded role plus ``contradictions``: an owner that names no solution, a part that names itself as owner, and a call its code makes to a solution
    that its role neither delegates to nor lists as one it uses. The part's code is every file named in the ``filepath`` of its implementations."""
    REQUIRES = ()     # reads the records folder and the part's own code

    def contradictions(self, part_id: str, role: Mapping[str, Any]) -> List[Dict[str, str]]:
        found = [{"code": UNKNOWN_OWNER, "detail": owner} for owner in role["delegates_to"] if owner not in self.solutions]
        found += [{"code": SELF_OWNER, "detail": part_id}] if part_id in role["delegates_to"] else []
        mine = [r for r in self.implementations if r.get("solution_id") == part_id]
        allowed = set(role["delegates_to"]) | {use for r in mine for use in split_ids(r.get("uses_solution_ids", ""))}
        called = [target for r in mine for target in calls_in(self.source(r.get("filepath", "")))]
        found += [{"code": UNDECLARED_CALL, "detail": target} for target in dict.fromkeys(called) if target not in allowed and target != part_id]
        return found

    def state_role(self, part_id: str) -> Mapping[str, Any]:
        role = dict(super().state_role(part_id))
        if role["stated"]:
            role["contradictions"] = self.contradictions(part_id, role)
        return role
