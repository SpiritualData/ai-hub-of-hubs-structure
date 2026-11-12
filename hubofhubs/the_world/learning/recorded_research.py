"""RecordedResearch: Learning's arm that makes research at runtime a recorded, reusable act (the systematic review plus a memory in the structure).

Before searching it finds the earlier investigations related to the request: the solutions the request serves (given as ``solution:`` links, else named by the
placer the caller hands in, in the consumer the relevant-solutions mechanism over its records) and the investigations linked to them or to the solutions above them,
read through the investigation store port. An earlier one with the same question, or one a fast-tier judgement says answers it, is reused when it is fresh and
at least as large as asked: nothing is searched and the record comes back with its date, synthesis and limitations to cite. A stale or smaller one is extended: only the
gap it left (what it said is not established, or what changed since) is searched and the same investigation is updated in place, never duplicated. With none, the
review runs as ``systematic_review`` does, sized by the weight of the decision (a question that informs no decision is a quick fact: not looked up, not recorded).

After searching it records the investigation through the store port (linked to the solutions and metrics), adds each kept finding as a knowledge item of the
solution it informs through the knowledge port (ensure-one; what a person wrote is never overwritten, and a location that holds the change for a person leaves the
finding marked as proposed), and puts one context item per investigation through the context port, fenced by the request's ``scope:<tag>`` links, so retrieval
surfaces it for related questions. A port that fails leaves the review as it was and says so in ``record_error``: recording never fails the answer.

The signature is the interface's; the returned record adds ``reused``, ``recorded``, ``searched``, ``searches`` (queries run), ``cited`` (what to say when building on
earlier research), ``knowledge`` (the answer of the knowledge port per finding) and ``updated`` (the investigation extended in place). The review's model calls stay the
fast tier; the reuse judgement is one extra fast-tier call, made only when related investigations exist and none has the same question.
"""
import copy
from datetime import date
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import Lazy, implementation, split_ids

from hubofhubs.the_world.learning import investigation_record as inv, investigation_store
from hubofhubs.the_world.learning.research_freshness_reader.interface import FreshnessReading
from hubofhubs.the_world.learning.research_ports import FolderKnowledge, FolderStore, norm, scope_of
from hubofhubs.the_world.learning.systematic_review import SystematicReview, as_hit, load_json
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing
from hubofhubs.the_world.science.interface import WorldKnowing
from hubofhubs.the_world.tools.web_search.interface import SearchBackend

PROMPT_REUSE = ("A question is about to be researched. Earlier investigations on the same solutions or ones above them are listed.\nQuestion: {question}\n"
                "Decision it informs: {decision}\nEarlier investigations (id | date | question | what it found):\n{rows}\n"
                "Reply with JSON only: {{\"answered_by\": \"<id of the one earlier investigation whose findings answer the question, copied exactly, or an empty string>\"}}. "
                "An investigation about a related but different question does not answer it. Use no em dashes.")
PROMPT_FACTS = ("A person asked a question and an answer was written from web results.\nQuestion: {question}\nDecision it informs: {decision}\nAnswer:\n{answer}\n"
                "Results seen (title: snippet):\n{evidence}\nReply with JSON only: {{\"known\": \"what the answer treats as settled, one or two sentences\", "
                "\"contested\": \"where sources or the answer disagree or hedge, or 'No disagreement seen.'\", \"unknown\": \"what is not established, one or two sentences\", "
                "\"moves\": \"fast, normal or slow: how quickly the facts on this subject go out of date\"}}. Use only the answer and the results. Use no em dashes.")
MOVES = {"fast": 14, "normal": None, "slow": 365}      # how fast the subject moves, as days to the revisit date (normal keeps the size's own)
KNOWN_FLOOR = "Nothing left unestablished"


class ReadReplay:
    """The pages a turn opened in full, served back to the review's page-opening step: a url the turn read returns its text, any other is not opened (so its item stays a snippet)."""

    def __init__(self, pages: Mapping[str, str]):
        self.pages = dict(pages)

    def fetch(self, url: str, *, focus: Any = None, **kwargs: Any):
        from hubofhubs.the_world.observation import Observation
        text = self.pages.get(url)
        return Observation(kind="read", text=text) if text else Observation(kind="error", error="not opened in this turn")
SAME_CELLS = ("investigation_id", "kind", "intent_id", "experiment_id", "question", "decision", "protocol_date", "method")


def cited(row: Mapping[str, str], state: str) -> Dict[str, str]:
    """What to say when building on earlier research: when it was done, how it stands and what it found and left open."""
    return {"investigation_id": row.get("investigation_id", ""), "done_on": row.get("done_on", ""), "refresh_on": row.get("refresh_on", ""), "state": state,
            "question": row.get("question", ""), "known": row.get("synthesis_known", ""), "unknown": row.get("synthesis_unknown", ""), "limitations": row.get("limitations", "")}


@implementation("the-learning", "recorded_research")
class RecordedResearch(SystematicReview):
    """Looks up related earlier investigations, reuses or extends them, records the new or updated one and its knowledge items and context item through ports."""
    REQUIRES = ()     # the seats it is handed; the ports are constructor arguments with the hub's own folders as defaults

    def __init__(self, freshness: FreshnessReading, science: Lazy[WorldKnowing], web: Lazy[SearchBackend], plumbing: Lazy[ModelPlumbing], tier: str = "fast",
                 ask: Optional[Callable[[str], str]] = None, store: Any = None, knowledge: Any = None, context: Any = None, placer: Any = None):
        super().__init__(freshness, science, web, plumbing, tier, ask)
        self.store, self.knowledge, self.context, self.placer = store, knowledge, context, placer

    def review(self, question: str, decision: str, weight: Any = None, size: str = "", links: Sequence[str] = (), criteria: Optional[Mapping[str, Any]] = None,
               candidates: Sequence[str] = (), queries: Sequence[str] = (), intent_id: str = "", experiment_id: str = "", today: str = "",
               refresh_days: Optional[int] = None, investigation_id: str = "", use_model: bool = False, solution_id: str = "", root: Any = None,
               reuse: bool = True) -> Mapping[str, Any]:
        day = today or date.today().isoformat()
        size = size or inv.choose_size(weight)
        rest = dict(criteria=criteria, candidates=candidates, intent_id=intent_id, experiment_id=experiment_id, today=day, refresh_days=refresh_days, use_model=use_model,
                    solution_id=solution_id, root=root)
        if not (decision or "").strip():      # a quick fact informs no decision: not looked up, not recorded, no more than the smallest review
            record = super().review(question, decision, size="quick", links=links, queries=queries, investigation_id=investigation_id, reuse=False, **rest)
            return {**record, "recorded": False, "searched": True, "searches": len(record["queries"]), "cited": {}, "knowledge": [], "updated": False}
        store = self.store or FolderStore(root)
        links = list(links)
        if not any(link.startswith("solution:") for link in links) and self.placer is not None:
            links += [f"solution:{s}" for s in self.placer(question, decision) if s]
        links, filed = investigation_store.with_solution(links, solution_id)
        solutions, scope = [link[9:] for link in links if link.startswith("solution:")], scope_of(links)
        earlier = self.earlier(store, question, decision, size, solutions, scope, day) if reuse else None
        if earlier and earlier["state"] == "fresh":
            record = investigation_store.record_of(earlier, root, store.items(earlier["investigation_id"]))
            return {**record, "solution_link": filed, "recorded": True, "searched": False, "searches": 0, "cited": cited(earlier, "fresh"), "knowledge": [], "updated": False}
        gap = self.gap_queries(question, earlier) if earlier else []
        record = super().review(question, decision, size=size, links=links, queries=list(queries) or gap, investigation_id=investigation_id, reuse=False, **rest)
        return self.finish(record, earlier, store, filed, solutions, scope, day, root)

    # --- recording research a turn already did ------------------------------------------------------------------------------------------
    def record_observed(self, question: str, decision: str, observed: Sequence[Mapping[str, Any]], answer: str = "", read: Optional[Mapping[str, str]] = None,
                        source_criteria: str = "", would_change: str = "", size: str = "quick", links: Sequence[str] = (), criteria: Optional[Mapping[str, Any]] = None,
                        intent_id: str = "", experiment_id: str = "", today: str = "", solution_id: str = "", root: Any = None) -> Mapping[str, Any]:
        """Record the research a turn already did, with no search. ``observed`` is each search the turn made (``{"query", "hits": [{title, url, snippet, date}]}``), ``read``
        the pages it opened in full (url to text), ``answer`` what it said, ``source_criteria`` and ``would_change`` the discipline stated before reading (what would count as a
        good source, what would change the conclusion). The record is the review's own (screening with a count for each reason, items graded A to D, a decision for each candidate) built
        from those hits; what is known, contested and unknown, and how fast the subject moves (the revisit date), come from one fast-tier call over the answer, and the rules' wording
        stands when it fails. A question with no decision is a quick fact and is not recorded. A fresh earlier investigation that answers the question is not duplicated (it is returned,
        ``reused``); a stale or smaller one is extended in place, as ``review`` does. Returns what ``review`` returns plus ``recorded``."""
        day = today or date.today().isoformat()
        if not (decision or "").strip() or not observed:
            return {"recorded": False, "reused": False, "searched": False, "searches": 0, "knowledge": [], "cited": {}, "updated": False}
        store = self.store or FolderStore(root)
        links = list(links)
        if not any(link.startswith("solution:") for link in links) and self.placer is not None:
            links += [f"solution:{s}" for s in self.placer(question, decision) if s]
        links, filed = investigation_store.with_solution(links, solution_id)
        solutions, scope = [link[9:] for link in links if link.startswith("solution:")], scope_of(links)
        earlier = self.earlier(store, question, decision, size, solutions, scope, day)
        if earlier and earlier["state"] == "fresh":
            record = investigation_store.record_of(earlier, root, store.items(earlier["investigation_id"]))
            return {**record, "solution_link": filed, "recorded": True, "searched": False, "searches": 0, "cited": cited(earlier, "fresh"), "knowledge": [], "updated": False, "reused": True}
        replay = copy.copy(self)
        replay.observed, replay.science, replay.facts = list(observed), ReadReplay(read or {}), replay.answer_facts(question, decision, answer, observed) if answer else {}
        record = SystematicReview.review(replay, question, decision, size=size, links=links, criteria=criteria, queries=[str(o.get("query") or "") for o in observed],
                                         intent_id=intent_id or (solutions[0] if solutions else ""), experiment_id=experiment_id, today=day,
                                         refresh_days=replay.facts.get("refresh_days"), solution_id=solution_id, root=root,
                                         reuse=False)
        row = record["investigation"]
        if source_criteria:
            row["criteria"] = f"{row['criteria']}. Sources that count, fixed before reading: {source_criteria}"
        if would_change:
            row["change_my_mind"] = would_change
        return self.finish(record, earlier, store, filed, solutions, scope, day, root)

    def answer_facts(self, question: str, decision: str, answer: str, observed: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        """One fast-tier extraction from the answer the turn gave: what is known, contested and not established, and how fast the subject moves (the revisit date)."""
        seen = "\n".join(f"- {h.get('title', '')}: {str(h.get('snippet', ''))[:160]}" for o in observed for h in (o.get("hits") or [])[:6])[:2400]
        data = load_json(self.say(PROMPT_FACTS.format(question=question, decision=decision, answer=answer[:3000], evidence=seen)))
        facts = {k: data[k].strip().replace(chr(0x2014), ",") for k in ("known", "contested", "unknown") if isinstance(data.get(k), str) and data[k].strip()}
        if len(facts) == 3 and data.get("moves") in MOVES:
            facts["refresh_days"] = MOVES[data["moves"]]
        return facts if len(facts) >= 3 else {}

    def search(self, plan: Sequence[str], kinds: Sequence[str], day: str, failures: Optional[List[str]] = None):
        """The review's search, or the turn's own searches when recording research already done (nothing is searched)."""
        if getattr(self, "observed", None) is None:
            return super().search(plan, kinds, day, failures)
        hits: List[Dict[str, str]] = []
        log: List[Dict[str, Any]] = []
        for o in self.observed:
            found = [as_hit(h) for h in o.get("hits") or []]
            log.append({"source": "web search", "query": str(o.get("query") or ""), "date": day, "hits": len(found)})
            hits += [dict(h, found_by="web search") for h in found]
        return hits, log, []

    def plan(self, question: str, candidates: Sequence[str], queries: Sequence[str], size: str) -> List[str]:
        return [str(q) for q in queries] if getattr(self, "observed", None) is not None else super().plan(question, candidates, queries, size)

    def synthesise(self, items, crit, question, decision, use_model):
        facts = getattr(self, "facts", None) or {}
        if facts.get("known"):
            return facts["known"], facts["contested"], facts["unknown"]
        return super().synthesise(items, crit, question, decision, use_model)

    def finish(self, record: Mapping[str, Any], earlier: Optional[Mapping[str, str]], store: Any, filed: Mapping[str, Any], solutions: Sequence[str], scope: Sequence[str], day: str,
               root: Any) -> Mapping[str, Any]:
        """The record, extended in place when it extends an earlier one, then kept: knowledge items, the investigation through the store port, the context item."""
        row, items = dict(record["investigation"]), [dict(i) for i in record["items"]]
        if earlier:
            row, items = self.extend(earlier, store.items(earlier["investigation_id"]), row, items, day)
        record_error = ""
        answers = self.add_knowledge(items, row, solutions, day, self.knowledge if self.knowledge is not None else FolderKnowledge(root))
        try:
            store.write({"investigation": row, "items": items})
        except Exception as error:     # recording never fails the answer
            record_error = f"the investigation could not be recorded: {error}"
        if self.context is not None and not record_error:
            try:
                self.context.put({"id": "investigation:" + row["investigation_id"], "investigation_id": row["investigation_id"], "question": row["question"], "decision": row["decision"],
                                  "known": row["synthesis_known"], "unknown": row["synthesis_unknown"], "limitations": row["limitations"], "done_on": row["done_on"],
                                  "refresh_on": row["refresh_on"], "solution_ids": solutions, "scope": scope})
            except Exception as error:
                record_error = f"the context item could not be put: {error}"
        out = {**record, "investigation": row, "items": items, "gaps": inv.gaps(row, items), "solution_link": filed, "recorded": not record_error, "searched": True,
               "searches": len(record["queries"]), "cited": cited(earlier, earlier["state"]) if earlier else {}, "knowledge": answers, "updated": bool(earlier),
               "extends": earlier["investigation_id"] if earlier else ""}
        return {**out, "record_error": record_error} if record_error else out

    # --- finding what is related ---------------------------------------------------------------------------------------------------------
    def earlier(self, store: Any, question: str, decision: str, size: str, solutions: Sequence[str], scope: Sequence[str], day: str) -> Optional[Dict[str, str]]:
        """The related earlier investigation to reuse or extend, with ``state`` (fresh, stale or partial), or None: the same question first, else the one a fast-tier
        judgement says answers it."""
        rows = store.related(solutions, scope, day)
        chosen = next((r for r in rows if norm(r.get("question", "")) == norm(question)), None)
        if chosen is None and rows:
            listing = "\n".join(f"{r['investigation_id']} | {r.get('done_on', '')} | {r.get('question', '')} | {r.get('synthesis_known', '')[:200]}" for r in rows[:8])
            wanted = str(load_json(self.say(PROMPT_REUSE.format(question=question, decision=decision, rows=listing))).get("answered_by") or "").strip()
            chosen = next((r for r in rows if r["investigation_id"] == wanted), None)
        if chosen is None:
            return None
        smaller = chosen.get("size") in inv.SIZES and inv.SIZES.index(chosen["size"]) < inv.SIZES.index(size)
        due = chosen.get("refresh_on") or ""
        return dict(chosen, state="partial" if smaller else "fresh" if due and due > day else "stale")

    def gap_queries(self, question: str, earlier: Mapping[str, str]) -> List[str]:
        """The queries that research only the gap: what the earlier investigation left unestablished, or what changed since it was done."""
        unknown = (earlier.get("synthesis_unknown") or "").strip()
        if unknown and not unknown.startswith(KNOWN_FLOOR):
            return [f"{question} {unknown.removeprefix('Not established:').strip()[:120]}".strip()]
        return [f"{question} since {earlier.get('done_on', '')}".strip()]

    # --- updating in place ----------------------------------------------------------------------------------------------------------------
    def extend(self, earlier: Mapping[str, str], old_items: Sequence[Mapping[str, str]], new_row: Mapping[str, str], new_items: Sequence[Dict[str, str]], day: str):
        """The earlier investigation with the new search added: the same id, the earlier items kept and the new ones numbered after them, the counts and queries summed."""
        row = {c: earlier.get(c, "") for c in inv.COLUMNS}
        known_ids = {i["item_id"] for i in old_items}
        items = [dict(i) for i in old_items]
        for n, item in enumerate(new_items, 1):
            item_id = f"e{day.replace('-', '')}-{n}"
            items.append(dict(item, item_id=item_id if item_id not in known_ids else f"{item_id}-{len(items)}", investigation_id=earlier["investigation_id"]))
        joined = lambda a, b: inv.SEP.join(x for x in (a, b) if x)      # noqa: E731
        found = int(earlier.get("found") or 0) + int(new_row.get("found") or 0)
        row.update(done_on=day, refresh_on=new_row["refresh_on"], size=new_row["size"] if inv.SIZES.index(new_row["size"]) > inv.SIZES.index(row["size"] or "quick") else row["size"],
                   queries=joined(row["queries"], new_row["queries"]), found=str(found), kept=str(len(items)), screened_out=joined(row["screened_out"], new_row["screened_out"]),
                   synthesis_known=f"{row['synthesis_known']} Extended on {day}: {new_row['synthesis_known']}".strip(),
                   synthesis_contested=new_row["synthesis_contested"], synthesis_unknown=new_row["synthesis_unknown"],
                   limitations=f"{row['limitations']}, extended on {day} by searching the gap the earlier record left", decisions=joined(new_row["decisions"], row["decisions"]),
                   links=inv.SEP.join(dict.fromkeys(split_ids(row["links"]) + split_ids(new_row["links"]))), status="open")
        return row, items

    # --- what each kept finding becomes in the structure ------------------------------------------------------------------------------
    def add_knowledge(self, items: Sequence[Dict[str, str]], row: Mapping[str, str], solutions: Sequence[str], day: str, sink: Any) -> List[Dict[str, Any]]:
        """Each finding graded A to C becomes a knowledge item of the solution it informs (the narrowest linked, the others named), and its ``applied`` cell says what came of it."""
        answers = []
        for item in items:
            if item.get("grade") not in ("A", "B", "C"):
                item["applied"] = f"not-applied: grade {item.get('grade') or 'D'} is too weak to keep as knowledge"
                continue
            knowledge_id = f"k-{solutions[0]}-{row['investigation_id']}-{item['item_id']}" if solutions else ""
            try:
                answer = dict(sink.add(solutions, item["claim"], item["source"], knowledge_id, row["investigation_id"], "evidence", day))
            except Exception as error:
                answer = {"status": "refused", "reason": str(error)}
            answers.append({"item_id": item["item_id"], **answer})
            status = answer.get("status")
            item["applied"] = (f"knowledge:{answer.get('target') or knowledge_id}" if status in ("applied", "unchanged")
                               else f"not-applied: the knowledge item is {status}, " + str(answer.get("reason") or "waiting for a person"))
        return answers
