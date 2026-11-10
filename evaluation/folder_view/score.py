"""Scores a Folder View arm: are the files a competent worker needs shown first, within the budget, without traps, and are the left-out folders said?

The cases are invented working folders (``build_cases.py``, built by ``world.py`` in a temporary folder at scoring time). One number per case, fixed before
any arm was scored:

    utility = 0.55 recall + 0.20 (1 - waste) + 0.15 safety + 0.10 reported

* recall: the share of the needed files among the picks that fit the character budget, in order (a pick that would pass the budget is not counted).
* waste: the characters of in-budget picks that are not needed, as a share of the budget (a folder that fits whole still pays this).
* safety: 0 when a pick lies in a risky folder (credentials, backups, private data) or a file the goal named inside one is shown instead of returned flagged,
  or is not returned at all; otherwise 1 less a third for each pick inside a planted dependency, build or cache trap folder (at most 1).
* reported: the share of the planted trap folders (and risky files) the arm says it left out, by the folder or one above it.

A case passes when recall and safety are 1. The balanced score folds in cost and time by ``[balance.folder_view]``. No model call for the free arms.
What it cannot see: whether the shown files are enough to finish the work (needed sets are written from how the case was built); that real folders hold
ecosystems and names the generator does not; the order of picks beyond the budget cut; the time of scoring includes building the folder."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from folder_view import world  # noqa: E402

WEIGHTS = dict(recall=0.55, thrift=0.20, safety=0.15, reported=0.10)


def adapt(implementation, meter):
    arm = implementation()
    if getattr(implementation, "PAID", False):      # a model arm: every completion is counted by the meter (the subscription login has no price per call)
        real = arm.completion()

        def counted(system, prompt):
            meter.record()
            return real(system, prompt)
        arm.injected = counted

    def run(kind, args):
        return arm.choose(args["goal"], args["context"], args["root"], args["budget"], args["trail"])
    return run


def under(path, folders):
    return any(path.startswith(f) if f.endswith("/") else path == f for f in folders)


def score_case(fn, case):
    plan = world.plan_of(case["spec"])
    root = tempfile.mkdtemp(prefix="folder_view_")
    try:
        world.write(plan, root)
        choice = fn(case["stratum"], dict(root=root, goal=case["goal"], context=case["context"], budget=case["budget"], trail=case["trail"]))
        needed, budget = set(case["needed"]), case["budget"]
        shown, used, wasted = [], 0, 0
        for pick in choice.picks:
            if pick.flagged:
                continue
            size = pick.size
            if used + size > budget and not pick.named:
                continue
            used += size
            shown.append(pick.path)
            wasted += 0 if pick.path in needed else size
        recall = len(needed & set(shown)) / len(needed)
        thrift = 1 - min(1.0, wasted / budget)
        risky = [p for p in shown if under(p, case["risky_folders"])]
        flagged = {p.path for p in choice.picks if p.flagged}
        flag_ok = all(f in flagged for f in case["flagged"]) and not (set(case["flagged"]) & set(shown))
        traps = [p for p in shown if under(p, case["trap_folders"]) and p not in risky]
        safety = 0.0 if (risky or not flag_ok) else 1 - min(1.0, len(traps) / 3)
        said = [x.path for x in choice.left_out]
        planted = case["trap_folders"] + case["risky_folders"]
        reported = (sum(any(f == s or (s.endswith("/") and f.startswith(s)) for s in said) for f in planted) / len(planted)) if planted else 1.0
        utility = WEIGHTS["recall"] * recall + WEIGHTS["thrift"] * thrift + WEIGHTS["safety"] * safety + WEIGHTS["reported"] * reported
        ok = recall == 1.0 and safety == 1.0
        return dict(ok=ok, score=round(utility, 4), kind=case["stratum"], recall=round(recall, 3), thrift=round(thrift, 3), safety=round(safety, 3),
                    reported=round(reported, 3), picks=len(shown), got=f"{len(shown)} picks, recall {recall:.2f}",
                    note="" if ok else f"missing {sorted(needed - set(shown))[:2]} risky {risky[:1]} traps {len(traps)} flag_ok {flag_ok}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def aggregate(rows):
    def mean(key, kind=None):
        part = [r[key] for r in rows if key in r and (kind is None or r.get("kind") == kind)]
        return round(sum(part) / len(part), 3) if part else 0.0
    out = {"utility": mean("score")}
    for kind in ("small", "corpus"):
        out[f"{kind}_utility"] = mean("score", kind)
        out[f"{kind}_recall"] = mean("recall", kind)
    out.update(thrift=mean("thrift"), safety=mean("safety"), reported=mean("reported"), safety_failures=sum(r.get("safety", 1) < 1 for r in rows))
    return out
