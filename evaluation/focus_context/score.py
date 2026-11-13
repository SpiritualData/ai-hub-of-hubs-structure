"""Scores a Focus Context arm: do the notes that reach the brief hold what the request needs, little else, and nothing outside the scope?

Cases are invented and neutral (``build_cases.py``, source tag ``invented-neutral``): the notes a person saved about a hobby focus, a distractor folder of notes that share its
words and a neighbour's notes in another scope. One number per case, weights fixed before any arm was scored:

    utility = 0.50 recall + 0.20 tidiness + 0.15 safety + 0.15 thrift

* recall: the share of the needed notes in the brief (a case that needs nothing scores 1 for it).
* tidiness: 1 less the share of the notes shown that are neither needed nor allowed (a note a case allows is one that may come along, such as the short overview of
  the focus); nothing shown scores 1.
* thrift: how much a judge was shown against what the case justifies. Each case says ``max_pages`` (pages of ``judge.PAGE_SIZE`` candidates the request justifies, fixed per kind in
  ``build_cases.py`` before any arm was scored). Thrift is 1 when the pages reviewed are within it, else ``max_pages / pages reviewed``; an arm that shows no judge anything
  (the free arms) reads 0 pages and scores 1. Under-review is not rewarded here: it shows as missing recall (a standing note the review stopped before reaching).
* safety: 0 when a note outside the request's scope is shown, otherwise 1.

A case passes when recall and safety are 1, tidiness is at least 0.5 and the pages reviewed are within the case's ``max_pages``. The one number is the share of cases passed; ``details`` carries the mean utility and the
mean recall, tidiness and safety per kind. No model call, no network: it scores which notes reach the brief, not what a model then writes. What it cannot see:
whether the answer uses the notes (the real run in ``tests`` of the terminal stage does), and real notes, whose words are less tidy than invented ones."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WEIGHTS = dict(recall=0.50, tidiness=0.20, safety=0.15, thrift=0.15)   # was recall .60 tidiness .25 safety .15 before the review amount was scored; fixed before the judged arm ran
PASS_TIDINESS = 0.5


def scripted_ask():
    """A stand-in judge that proves the plumbing with no model (``FOCUS_CONTEXT_JUDGE=scripted``): it names, in the prompt's numbering, the notes the case marks as needed or
    allowed (the oracle, so it bounds what a perfect judge scores, and it says nothing about a model). Both views answer alike."""
    import json
    import re
    wanted = {}
    for c in json.loads((Path(__file__).resolve().parent / "cases.json").read_text()):
        wanted[(c["args"]["request"], tuple(n["id"] for n in c["args"]["notes"]))] = set(c["expect"]["needed"]) | set(c["expect"]["allowed"])
    state = {}

    def ask(prompt):
        request = prompt.split("Request:\n", 1)[1].split("\n\nCandidate notes", 1)[0].strip()
        titles = [(int(n), t) for n, t in re.findall(r"^\[(\d+)\] (.*?): ", prompt, re.M)]
        ids = state["by_title"]
        return json.dumps({"relevant": [n for n, t in titles if ids.get((request, t)) in wanted.get(state["key"], set())]})
    return ask, state, wanted


class Got(list):
    """The ids an arm put in the brief, and (for a judged arm) what its judge reviewed: ``review`` = pages, candidates shown, model calls."""
    review = None


def adapt(implementation, meter):
    arm = implementation()
    judge = getattr(arm, "judge", None)
    if judge is not None:           # a model arm: every completion is counted by the meter; FOCUS_CONTEXT_JUDGE=scripted swaps in the oracle stand-in (nothing is spent)
        import os
        if os.environ.get("FOCUS_CONTEXT_JUDGE") == "scripted":
            ask, state, _ = scripted_ask()
            meter.model = "simulated"
            judge.injected = ask
            inner = arm.gather

            def gather(request, notes, **kw):
                state["key"] = (request, tuple(n["id"] for n in notes))
                state["by_title"] = {(request, n["title"]): n["id"] for n in notes}
                return inner(request, notes, **kw)
            arm.gather = gather
        else:
            from hubofhubs.the_intelligence.subconscious.focus_context.judge import fast_ask
            real = fast_ask(judge.tier, judge.used)
            meter.model = getattr(real, "model", None)

            def counted(prompt):
                meter.record()
                return real(prompt)
            counted.model = real.model
            judge.injected = counted

    def run(kind, args):
        got = Got(arm.gather(args["request"], args["notes"], focus=args["focus"], max_notes=args.get("max_notes", 5), budget_tokens=1500, scope=args["scope"]).ids)
        if judge is not None:
            got.review = dict(arm.review)
            meter.tokens_in, meter.tokens_out, meter.cost_usd = judge.tokens_in, judge.tokens_out, judge.cost_usd
        return got
    return run


def score_case(fn, case):
    fn_result = fn(case["kind"], case["args"])
    got = list(fn_result)
    want, allowed, fenced = case["expect"]["needed"], set(case["expect"]["allowed"]), set(case["expect"]["fenced"])
    recall = (len(set(got) & set(want)) / len(want)) if want else 1.0
    noise = [i for i in got if i not in want and i not in allowed]
    tidiness = 1.0 - (len(noise) / len(got)) if got else 1.0
    safety = 0.0 if set(got) & fenced else 1.0
    review = getattr(fn_result, "review", None) or {"pages": 0, "reviewed": 0, "calls": 0}
    allowed_pages = case["expect"].get("max_pages", 99)
    thrift = 1.0 if review["pages"] <= allowed_pages else allowed_pages / review["pages"]
    utility = WEIGHTS["recall"] * recall + WEIGHTS["tidiness"] * tidiness + WEIGHTS["safety"] * safety + WEIGHTS["thrift"] * thrift
    ok = recall == 1.0 and safety == 1.0 and tidiness >= PASS_TIDINESS and review["pages"] <= allowed_pages
    return dict(ok=ok, score=round(utility, 4), kind=case["kind"], recall=round(recall, 3), tidiness=round(tidiness, 3), safety=safety, thrift=round(thrift, 3), pages=review["pages"],
                reviewed=review["reviewed"], judge_calls=review["calls"], got=",".join(got)[:70],
                note="" if ok else f"missing {sorted(set(want) - set(got))[:2]} noise {noise[:2]} fenced {sorted(set(got) & fenced)} pages {review['pages']}/{allowed_pages}")


def aggregate(rows):
    def mean(key, kind=None):
        part = [r[key] for r in rows if key in r and (kind is None or r.get("kind") == kind)]
        return round(sum(part) / len(part), 3) if part else 0.0
    out = {"utility": mean("score"), "recall": mean("recall"), "tidiness": mean("tidiness"), "safety": mean("safety"), "thrift": mean("thrift"), "reviewed_mean": mean("reviewed"),
           "judge_calls_mean": mean("judge_calls"), "fenced_shown": sum(r.get("safety", 1) < 1 for r in rows)}
    for kind in sorted({r["kind"] for r in rows}):
        out[f"{kind}_utility"] = mean("score", kind)
        out[f"{kind}_reviewed"] = mean("reviewed", kind)
    return out
