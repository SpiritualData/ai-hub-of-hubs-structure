"""Decision Check arms: small independent checks that check each other's work, so a cheap model gives a reliable decision through structure.

``agreement_check`` runs one short structured call per view in parallel (each sees only its slice of evidence), adds the producer's own pick and any vote the consumer already holds, and
reconciles by agreement: when the opinions agree the decision is accepted at no further cost; when they disagree one adjudication call sees only the disagreeing views, their evidence and
quotes and the options, and must quote the deciding words (code checks they are in that evidence) or the result abstains. For a reply, each view lists the spans that fail, code checks
each span is in the reply, independent confirmation calls (two, a third only on a split) judge each span, and only a confirmed span is rewritten or removed, with the evidence that contradicts it;
each stage starts as soon as its input is in, on one pool of bounded width.
``agreement_with_known_mistakes`` is the same arm with each view's known-mistake lines in its prompt and, while the call budget allows, a twin view built on them.
``majority_vote`` is the agreement check with a disagreement settled by the views' majority (a tie still goes to the adjudication). ``single_verify`` is the one verify call that was tried before (the bound), and ``draft_as_given`` makes no call. Every arm stays within ``max_calls``. Standard library plus the hub and ``esoi``."""
import re
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi import Lazy

from hubofhubs.the_intelligence.critical_thinking.decision_check.checks import (
    ABSTAIN, ADJUDICATE_PROMPT, CONFIRM_PROMPT, CallPool, FINDINGS_PROMPT, PICK, REPAIR_PROMPT, REPLY, Calls, CheckBinding, View, Vote, as_binding,
    known_block, numbered, parse_json, pick_view_prompt, quoted, read_pick, read_verdicts, remove_span, run_parallel, sentence_of, spent_view, options_listing)
from hubofhubs.the_intelligence.critical_thinking.decision_check.mistakes import CONFIRMED_FAILURE, new_mistake
from hubofhubs.the_intelligence.critical_thinking.decision_check.remainder import cohere, complete, figures, joined, units_of
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing


CONFIRMATIONS = 3          # independent confirmations a flagged span can get; most of them must say it fails
FIRST_CONFIRMATIONS = 2    # asked first; when they agree the third cannot change the majority, so it is asked only on a split
UNCONFIRMED_REPLY = "I could not confirm the answer from what I read this turn, so I have left out what I could not confirm."


def result(outcome: str, calls: Calls, why: str, agreement: float, **fields: Any) -> Dict[str, Any]:
    return dict({"outcome": outcome, "calls": calls.used, "limit": calls.limit, "agreement": round(agreement, 3), "why": why}, **fields)


class Asking:
    """The model call of a decision: counts against the budget, and a failed call is a view that did not answer (the reason is kept), never a silent default."""

    def __init__(self, ask: Callable[[str], str], calls: Calls):
        self.ask, self.calls = ask, calls

    def __call__(self, prompt: str) -> Optional[str]:
        if not self.calls.take():
            return None
        try:
            return self.ask(prompt)
        except Exception as error:  # noqa: BLE001 -- a failed call is a view that did not answer
            return "ERROR " + type(error).__name__


class Arm:
    """What the model-calling arms share: the model, the tier, and the `check` entry point that picks the flow for the binding's kind."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True
    use_known = False

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "cheap"):
        self.plumbing, self.tier = plumbing, tier

    def check(self, draft: Any, binding: Any, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        b = as_binding(binding)
        calls = Calls(b.max_calls)
        model = Asking(ask if ask is not None else (lambda prompt: self.plumbing.ask(prompt, self.tier)), calls)
        return self.check_reply(str(draft or ""), b, model, calls) if b.kind == REPLY else self.check_pick(str(draft or ""), b, model, calls)

    def planned_views(self, b: CheckBinding, reserve: int) -> List[View]:
        """The views to run: the binding's, and (known-mistake arm only) a twin of each view that has lines while the budget keeps ``reserve`` calls for what follows."""
        views = list(b.views)[:max(0, b.max_calls - reserve)]
        if not self.use_known:
            return views
        out = list(views)
        for view in views:
            lines = b.known.get(view.id, ())
            if lines and len(out) + reserve < b.max_calls:
                twin = View(view.id + "+known", "Take most care over these known mistakes of this check:\n" + "\n".join(f"- {line}" for line in lines) + "\n" + view.instruction, view.evidence)
                out.append(twin)
        return out

    def prompt_binding(self, b: CheckBinding) -> CheckBinding:
        return b if self.use_known else CheckBinding(**dict(vars(b), known={}))

    # ---- a pick among options
    def check_pick(self, draft: str, b: CheckBinding, model: Asking, calls: Calls) -> Dict[str, Any]:
        ids = {str(o.get("id")) for o in b.options}
        shown = self.prompt_binding(b)
        views = self.planned_views(b, 1)

        def one(view: View) -> Dict[str, Any]:
            raw = model(pick_view_prompt(view, shown))
            return spent_view(view.id, "the call budget was used") if raw is None else dict(read_pick(raw, view.id, view.evidence, b.options), evidence=view.evidence, asked=view.instruction)
        read = run_parallel([lambda v=v: one(v) for v in views], b.parallel)
        cast = [dict(r) for r in read if r["pick"]]
        if draft in ids:
            cast.append({"id": "draft", "pick": draft, "quote": b.draft_basis, "evidence": b.draft_basis, "asked": "the draft pick", "reason": ""})
        cast += [{"id": v.id, "pick": v.pick, "quote": v.quote, "evidence": v.evidence or v.quote, "asked": "a vote the caller already held", "reason": ""} for v in b.votes if v.pick in ids]
        report = [{k: r.get(k, "") for k in ("id", "pick", "quote", "reason")} for r in read + [c for c in cast if c["id"] not in {r["id"] for r in read}]]
        picks = sorted({c["pick"] for c in cast})
        if not picks:
            return result("kept", calls, "no view had an opinion and there was no draft pick", 0.0, pick="", views=report)
        if len(picks) == 1:
            only_draft = all(c["id"] == "draft" for c in cast)
            return result("kept" if only_draft else "agreed", calls, "no view had an opinion, so the draft stands" if only_draft else "the opinions agree", 1.0, pick=picks[0], views=report)
        return self.adjudicate(cast, picks, b, model, calls, report)

    def adjudicate(self, cast: List[Dict[str, Any]], picks: List[str], b: CheckBinding, model: Asking, calls: Calls, report: List[Dict[str, Any]]) -> Dict[str, Any]:
        largest = max(sum(c["pick"] == p for c in cast) for p in picks) / len(cast)
        shown = "\n\n".join(f"[{c['id']}] was asked: {c['asked']}\nIt picked {c['pick']}.\nEvidence it saw:\n{c['evidence'] or '(none)'}\nIt quoted: \"{c['quote']}\"" for c in cast)
        raw = model(ADJUDICATE_PROMPT.format(options=options_listing(b.options), views=shown, abstain=ABSTAIN))
        if raw is None:
            return result("abstained", calls, "the opinions disagree and no call was left to decide", largest, pick="", views=report)
        data = parse_json(raw)
        pick, quote = data.get("pick"), data.get("quote")
        deciding = "\n".join(str(c["evidence"]) + "\n" + str(c["quote"]) for c in cast)
        if isinstance(pick, str) and pick.strip().upper() == ABSTAIN:
            return result("abstained", calls, "the adjudication found the evidence does not decide", largest, pick="", views=report)
        if not isinstance(pick, str) or pick.strip() not in picks:
            return result("abstained", calls, "the adjudication named none of the options the views picked", largest, pick="", views=report)
        if not quoted(quote, deciding):
            return result("abstained", calls, "the adjudication did not quote the deciding words from the evidence", largest, pick="", views=report)
        final = pick.strip()
        return result("adjudicated", calls, "the opinions disagreed; the adjudication quoted the deciding evidence", sum(c["pick"] == final for c in cast) / len(cast),
                      pick=final, quote=str(quote).strip(), overruled=[c["id"] for c in cast if c["pick"] != final], views=report)

    # ---- a reply
    def check_reply(self, draft: str, b: CheckBinding, model: Asking, calls: Calls) -> Dict[str, Any]:
        """Every stage starts as soon as what it needs is in, on one pool of at most ``b.parallel`` calls in flight (a provider's limit on concurrent calls is the usual
        cause of slow checks, so the width is a ceiling, not a target): a view's flagged spans go to confirmation the moment that view answers, and a confirmed span
        goes to repair the moment it is confirmed. A view's spans are confirmed together, each judged on its own in the list. Two confirmations come first; when they
        agree the third cannot change the majority, so it is asked only on a split. With ``hedge_after_seconds`` a call still unanswered that long is sent once more and
        the first answer wins. Every flagged span is confirmed (those calls run on top of the cap) and no confirmed span ships unchanged."""
        shown = self.prompt_binding(b)
        views = self.planned_views(b, 2)
        by_id = {v.id: v for v in views}
        raised = 0
        grounded: List[Dict[str, Any]] = []
        votes: Dict[int, List[Dict[str, Any]]] = {}
        waiting: Dict[int, int] = {}
        asked: Dict[int, int] = {}
        verdict: Dict[int, bool] = {}
        repairs: Dict[int, Dict[str, Any]] = {}

        def hedge() -> None:
            calls.limit += 1          # a hedge repeats a call already counted, so it never takes the place of a repair
        pool = CallPool(model, b.parallel, b.hedge_after_seconds, on_hedge=hedge)
        try:
            def confirm(view: View, idxs: List[int], times: int) -> None:
                calls.limit += times      # confirmations run on top of the cap
                prompt = CONFIRM_PROMPT.format(instruction=view.instruction, statements=numbered([grounded[i]["span"] for i in idxs]), evidence=view.evidence)
                for i in idxs:
                    waiting[i] = waiting.get(i, 0) + times
                    asked[i] = asked.get(i, 0) + times
                for _ in range(times):
                    pool.submit(("confirm", idxs), prompt)

            def repair(i: int) -> None:
                f = grounded[i]
                view = by_id[f["view"]]
                quote = next((a["quote"] for a in votes[i] if a["fails"] and a["quote"]), f["quote"])
                evidence = quote if quoted(quote, view.evidence) else view.evidence
                # The words that contradict the span, checked by code to be in the evidence: a rewrite may state their figures (the corrected count), never others.
                f.update(quote=quote, basis=quote if quoted(quote, view.evidence) else "")
                prompt = REPAIR_PROMPT.format(instruction=view.instruction, sentence=sentence_of(draft, f["span"]), span=f["span"], evidence=evidence)
                pool.submit(("repair", i), prompt)

            for view in views:
                prompt = FINDINGS_PROMPT.format(instruction=view.instruction, draft=draft, evidence=view.evidence, known=known_block(shown.known.get(view.id, ()), b.token_cap))
                pool.submit(("view", view), prompt)
            while pool.busy():
                for (stage, what), raw in pool.next_answers():
                    if stage == "view":
                        rows = parse_json(raw).get("findings") if raw is not None else None
                        mine = []
                        for r in rows if isinstance(rows, list) else ():
                            if not isinstance(r, dict):
                                continue
                            raised += 1
                            span = str(r.get("span") or "")
                            if span and span in draft and span not in {g["span"] for g in grounded}:
                                mine.append(len(grounded))
                                grounded.append({"view": what.id, "span": span, "quote": str(r.get("quote") or "")})
                        if mine:
                            confirm(what, mine, FIRST_CONFIRMATIONS)
                    elif stage == "confirm":
                        read = read_verdicts(raw, len(what)) if raw is not None else {}
                        split: List[int] = []
                        for k, i in enumerate(what):
                            waiting[i] -= 1
                            if raw is not None:
                                votes.setdefault(i, []).append(read.get(k) or {"fails": False, "quote": ""})
                            if waiting[i] or i in verdict:
                                continue
                            fails = sum(a["fails"] for a in votes.get(i, []))
                            holds = len(votes.get(i, [])) - fails
                            if 2 * fails > CONFIRMATIONS or 2 * holds > CONFIRMATIONS or asked[i] >= CONFIRMATIONS:
                                verdict[i] = 2 * fails > len(votes.get(i, [])) > 0
                                if verdict[i]:
                                    repair(i)
                            else:
                                split.append(i)
                        if split:
                            confirm(by_id[grounded[split[0]]["view"]], split, 1)
                    else:
                        f = grounded[what]
                        data = parse_json(raw) if raw is not None else {}
                        action, text = data.get("action"), str(data.get("text") or "").strip()
                        # A rewrite states no figure that neither the span nor the quoted evidence that contradicts it states (compared by value: "1,000" is
                        # "1000", "02" is "2"). Measured 2026-11-11: with only the span's figures allowed, a correct count corrected from the evidence ("1 of
                        # 43 done") became a removal, and the reply lost the goal it was about.
                        if action == "rewrite" and text and text != f["span"] and not figures(text) - figures(f["span"]) - figures(f.get("basis") or ""):
                            repairs[what] = dict(f, action="rewrite", text=text)
                        else:
                            why = ("no call was left for a rewrite" if raw is None else "the rewrite added a figure the reply did not state" if action == "rewrite" and text
                                   else "the repair removed it" if action == "remove" else "the repair gave no usable rewrite")
                            repairs[what] = dict(f, action="remove", text="", why_removed=why)
        finally:
            pool.close()
        if not grounded:
            return result("held", calls, "no view found a failing span in the reply", 1.0, text=draft, findings=[], dropped=raised, hedged=pool.hedged)
        checked = [dict(f, asked=len(votes.get(i, [])), confirmed=verdict.get(i, False), votes=sum(a["fails"] for a in votes.get(i, []))) for i, f in enumerate(grounded)]
        confirmed = [i for i in range(len(grounded)) if verdict.get(i)]
        agreement = len(confirmed) / len(grounded)
        if not confirmed:
            return result("held", calls, "most confirmations found none of the raised spans to fail", agreement, text=draft, findings=checked, dropped=raised - len(grounded), hedged=pool.hedged)
        done_repairs = [dict(repairs[i], asked=checked[i]["asked"], confirmed=True, votes=checked[i]["votes"]) for i in confirmed]
        units = units_of(draft)
        removed_any = False
        for r in done_repairs:
            holder = next((u for u in units if u.kept and r["span"] in u.text), None)
            # A span may run over several sentences: then it is those sentences.
            held = [holder] if holder is not None else [u for u in units if u.kept and u.text in r["span"]]
            if not held:
                continue
            if r["action"] == "rewrite":
                was = held[0].text
                held[0].text = held[0].text.replace(r["span"], r["text"], 1) if holder is not None else r["text"]
                for u in held[1:]:
                    u.kept = False
                if complete(was) and not complete(held[0].text):
                    # A rewrite that leaves a fragment ("The step is due") says less than nothing: the whole sentence is removed instead, and what is left is cohered.
                    held[0].text, held[0].kept = was, False
                    r.update(action="remove", text="", why_removed="the rewrite left an incomplete sentence")
                    removed_any = True
            else:
                # Code removes the confirmed span with the whole sentence that holds it: a clause cut out of its sentence leaves a fragment that says nothing.
                for u in held:
                    u.kept = False
                removed_any = True
        cohered = "coherent"
        if removed_any and any(u.kept for u in units):
            # What is left must still read as an answer: a sentence pointing back to a removed one ("Its value", "the same figure") is rewritten from the rest, or removed.
            calls.limit += 1
            units, cohered = cohere(units, b.question, model)
        out = joined(units)
        if not out.strip():
            out = UNCONFIRMED_REPLY
        mistakes = [asdict(new_mistake(r["view"], by_id[r["view"]].evidence[:2000], r["span"], r.get("why_removed") or "", CONFIRMED_FAILURE))
                    for r in done_repairs if r["action"] != "rewrite"]
        return result("repaired", calls, "every confirmed failing span was rewritten or removed", agreement, text=out, findings=done_repairs, mistakes=mistakes,
                      dropped=raised - len(grounded), hedged=pool.hedged, cohered=cohered)


@implementation("decision-check", "agreement_check")
class AgreementCheck(Arm):
    """Independent views in parallel, reconciled by agreement, one adjudication only on a disagreement, targeted repair of a reply. See the module text."""


@implementation("decision-check", "agreement_with_known_mistakes")
class AgreementWithKnownMistakes(Arm):
    """The agreement check with each view's known-mistake lines in its prompt and a twin view built on them while the call budget allows."""
    use_known = True


@implementation("decision-check", "majority_vote")
class MajorityVote(Arm):
    """The agreement check with a disagreement settled by the views' majority: each view's pick stands only with a quote code finds in its evidence, and the pick more than
    half of the opinions hold is the decision. Only a tie (no pick held by more than half) goes to the adjudication call. Several views of the same question, each a
    separate cheap call, make the decision independent of any one sample."""

    def adjudicate(self, cast: List[Dict[str, Any]], picks: List[str], b: CheckBinding, model: Asking, calls: Calls, report: List[Dict[str, Any]]) -> Dict[str, Any]:
        counts = {p: sum(c["pick"] == p for c in cast) for p in picks}
        top = max(counts.values())
        leaders = [p for p in picks if counts[p] == top]
        if len(leaders) == 1 and 2 * top > len(cast):
            return result("majority", calls, f"{top} of {len(cast)} opinions hold the pick", top / len(cast), pick=leaders[0],
                          overruled=[c["id"] for c in cast if c["pick"] != leaders[0]], views=report)
        return super().adjudicate(cast, picks, b, model, calls, report)


@implementation("decision-check", "single_verify")
class SingleVerify(Arm):
    """One verify call shown all the evidence at once and the draft: the way it was tried before, kept as the bound. A pick is the call's pick when it quotes the evidence; a reply loses the spans the call lists."""

    def check_pick(self, draft: str, b: CheckBinding, model: Asking, calls: Calls) -> Dict[str, Any]:
        merged = View("all", f"A draft picked option {draft}. Decide which option is right. " + " ".join(v.instruction for v in b.views), "\n\n".join(v.evidence for v in b.views))
        row = read_pick(model(pick_view_prompt(merged, self.prompt_binding(b))), "all", merged.evidence, b.options)
        if not row["pick"]:
            return result("kept", calls, "the one call did not decide: " + row["reason"], 1.0, pick=draft, views=[row])
        return result("agreed" if row["pick"] == draft else "adjudicated", calls, "one call over all the evidence", 1.0 if row["pick"] == draft else 0.0, pick=row["pick"], views=[row])

    def check_reply(self, draft: str, b: CheckBinding, model: Asking, calls: Calls) -> Dict[str, Any]:
        instruction = " ".join(v.instruction for v in b.views)
        raw = model(FINDINGS_PROMPT.format(instruction=instruction, draft=draft, evidence="\n\n".join(v.evidence for v in b.views), known=""))
        rows = parse_json(raw).get("findings") if raw is not None else None
        spans = [str(r.get("span") or "") for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
        out = draft
        for span in dict.fromkeys(s for s in spans if s and s in draft):
            out = remove_span(out, span)
        return result("repaired" if out != draft else "held", calls, "one call over all the evidence", 1.0, text=out, findings=[{"span": s} for s in spans])


@implementation("decision-check", "draft_as_given")
class DraftAsGiven:
    """The draft stands as produced and no call is made: the floor every other arm must beat."""
    REQUIRES = ()     # nothing

    def check(self, draft: Any, binding: Any, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        b = as_binding(binding)
        calls = Calls(0)
        return result("kept", calls, "the draft was not checked", 1.0, **({"text": str(draft or "")} if b.kind == REPLY else {"pick": str(draft or "")}))
