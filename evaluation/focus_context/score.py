"""Scores a Focus Context arm: do the notes that reach the brief hold what the request needs, little else, and nothing outside the scope?

Cases are invented and neutral (``build_cases.py``, source tag ``invented-neutral``): the notes a person saved about a hobby focus, a distractor folder of notes that share its
words and a neighbour's notes in another scope. One number per case, weights fixed before any arm was scored:

    utility = 0.60 recall + 0.25 tidiness + 0.15 safety

* recall: the share of the needed notes in the brief (a case that needs nothing scores 1 for it).
* tidiness: 1 less the share of the notes shown that are neither needed nor allowed (a note a case allows is one that may come along, such as the short overview of
  the focus); nothing shown scores 1.
* safety: 0 when a note outside the request's scope is shown, otherwise 1.

A case passes when recall and safety are 1 and tidiness is at least 0.5. The one number is the share of cases passed; ``details`` carries the mean utility and the
mean recall, tidiness and safety per kind. No model call, no network: it scores which notes reach the brief, not what a model then writes. What it cannot see:
whether the answer uses the notes (the real run in ``tests`` of the terminal stage does), and real notes, whose words are less tidy than invented ones."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WEIGHTS = dict(recall=0.60, tidiness=0.25, safety=0.15)
PASS_TIDINESS = 0.5


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        return arm.gather(args["request"], args["notes"], focus=args["focus"], max_notes=5, budget_tokens=1500, scope=args["scope"]).ids
    return run


def score_case(fn, case):
    got = list(fn(case["kind"], case["args"]))
    want, allowed, fenced = case["expect"]["needed"], set(case["expect"]["allowed"]), set(case["expect"]["fenced"])
    recall = (len(set(got) & set(want)) / len(want)) if want else 1.0
    noise = [i for i in got if i not in want and i not in allowed]
    tidiness = 1.0 - (len(noise) / len(got)) if got else 1.0
    safety = 0.0 if set(got) & fenced else 1.0
    utility = WEIGHTS["recall"] * recall + WEIGHTS["tidiness"] * tidiness + WEIGHTS["safety"] * safety
    ok = recall == 1.0 and safety == 1.0 and tidiness >= PASS_TIDINESS
    return dict(ok=ok, score=round(utility, 4), kind=case["kind"], recall=round(recall, 3), tidiness=round(tidiness, 3), safety=safety, got=",".join(got)[:70],
                note="" if ok else f"missing {sorted(set(want) - set(got))[:2]} noise {noise[:2]} fenced {sorted(set(got) & fenced)}")


def aggregate(rows):
    def mean(key, kind=None):
        part = [r[key] for r in rows if key in r and (kind is None or r.get("kind") == kind)]
        return round(sum(part) / len(part), 3) if part else 0.0
    out = {"utility": mean("score"), "recall": mean("recall"), "tidiness": mean("tidiness"), "safety": mean("safety"), "fenced_shown": sum(r.get("safety", 1) < 1 for r in rows)}
    for kind in sorted({r["kind"] for r in rows}):
        out[f"{kind}_utility"] = mean("score", kind)
    return out
