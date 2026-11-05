"""Rebuild cases.json for Role Understanding. Two kinds, each case tagged with its ``origin``:

``record``  the role of a part as a row of solutions.csv states it, in the shapes the scoping how-to describes (purpose, out_of_scope, owners in ``delegates_to``
            separated by semicolons, ``none`` for no owner, an empty field, stray spaces) and a part id no record knows, which must come back unstated
            (origin: written from the records format and docs/how-to/scope-the-role-of-a-solution.md in esoi; fixed rows, so a later edit of the hub's own words
            never changes what an arm is scored against).
``contradiction``  a role set written from the failure kinds esoi's S48 names (an owner that is no solution) and the call-versus-declaration mismatch rule
            S50 reads (a part whose code calls a solution it neither uses nor delegates to), each with the codes an honest checker reports and consistent
            twins that must report none (origin: written from esoi rules S48 and S50).

    python3 evaluation/role_understanding/build_cases.py

Standard library plus ``esoi``."""
import json
from pathlib import Path

from esoi import split_ids

HERE = Path(__file__).resolve().parent

ORIGIN_RECORD = "written from the records format and the esoi role-scoping how-to"


def sol(ident, owners="", scope="Other parts' work."):
    return {"solution_id": ident, "purpose": f"Does the job of {ident}.", "out_of_scope": scope, "delegates_to": owners}


def impl(ident, uses="", path=""):
    return {"solution_id": ident, "uses_solution_ids": uses, "filepath": path}


def written(name, solutions, implementations, code, part, codes):
    return {"id": "role-contradiction-" + name, "kind": "contradiction", "origin": "written from esoi rules S48 and S50",
            "args": {"solutions": solutions, "implementations": implementations, "code": code, "part": part}, "expect": {"contradictions": sorted(codes)}}


def main():
    cases = []
    rows = [{"solution_id": "alpha", "purpose": "  Keeps the ledger. ", "out_of_scope": "Auditing it.", "delegates_to": "beta;gamma"},
            {"solution_id": "beta", "purpose": "Audits the ledger.", "out_of_scope": "Keeping it.", "delegates_to": "alpha"},
            {"solution_id": "solo", "purpose": "Does the one job.", "out_of_scope": "Nothing else exists.", "delegates_to": "none"},
            {"solution_id": "blank", "purpose": "Has a purpose.", "out_of_scope": "", "delegates_to": ""}]
    for row in rows:
        want = {"part": row["solution_id"], "stated": True, "purpose": row["purpose"].strip(), "out_of_scope": row["out_of_scope"].strip(),
                "delegates_to": [o for o in split_ids(row["delegates_to"]) if o != "none"]}
        cases.append({"id": "role-record-" + row["solution_id"], "kind": "record", "origin": ORIGIN_RECORD, "args": {"part": row["solution_id"], "solutions": rows}, "expect": want})
    cases.append({"id": "role-record-unknown-part", "kind": "record", "origin": ORIGIN_RECORD, "args": {"part": "no-such-part", "solutions": rows},
                  "expect": {"part": "no-such-part", "stated": False}})
    flow = 'take(self.a, "b")\ntake(self.c, "c-part", method="m")\n'
    cases += [
        written("owner-is-no-solution", [sol("p", "ghost")], [impl("p")], {}, "p", ["unknown-owner"]),
        written("owner-is-itself", [sol("p", "p")], [impl("p")], {}, "p", ["self-owner"]),
        written("calls-a-part-it-never-declared", [sol("p", "b"), sol("b"), sol("c-part")], [impl("p", "b", "p.py")], {"p.py": flow}, "p", ["undeclared-call"]),
        written("both-kinds", [sol("p", "ghost"), sol("c-part")], [impl("p", "", "p.py")], {"p.py": flow}, "p", ["unknown-owner", "undeclared-call", "undeclared-call"]),
        written("calls-only-what-it-uses", [sol("p"), sol("b"), sol("c-part")], [impl("p", "b;c-part", "p.py")], {"p.py": flow}, "p", []),
        written("calls-only-what-it-delegates", [sol("p", "b;c-part"), sol("b"), sol("c-part")], [impl("p", "", "p.py")], {"p.py": flow}, "p", []),
        written("no-code-no-contradiction", [sol("p", "b"), sol("b")], [impl("p")], {}, "p", []),
        written("calls-with-a-variable-id-are-not-guessed", [sol("p"), sol("b")], [impl("p", "", "p.py")], {"p.py": "take(self.a, name)\n"}, "p", []),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
