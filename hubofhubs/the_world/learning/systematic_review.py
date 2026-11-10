"""SystematicReview: Learning's arm that does a knowledge search as a small systematic review (the ESOI library's research standard).

``review`` takes a research question and the decision it informs, sizes the review by the decision's weight, fixes and dates the method before the first query,
runs the queries through the hub's own Web Search and The Science seats (typed needs, never a consumer), screens with a count for each reason, extracts and
grades each kept item by the library's A to D rule, opens a few kept pages to verify them (standard and full), synthesises what is known, contested and unknown,
decides for each candidate, states what each item changed (the applied part) and sets the date to revisit. It returns the record the standard defines
(``investigation_record.Investigation``, an investigation of kind review). Screening, extraction, grading and the decisions are rules; with ``use_model`` a fast-tier model also drops results that do not
bear on the question and writes the synthesis, at most two calls, and its failure leaves the rules' answer.

``due_investigations`` is what a consumer's autopilot asks: the investigations past their revisit date, the experiments past their reevaluation time and the registry areas whose research is stale, each with the request
to run (``investigation_store.due``); ``standing_schedule`` is the weekly refresh as a schedule Proactivity reads. Standard library plus the hub and ``esoi``.
"""
import json
import re
from datetime import date
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

from esoi import Lazy, implementation

from hubofhubs.the_world.learning import investigation_record as inv, investigation_store
from hubofhubs.the_world.learning.research_freshness_reader.interface import FreshnessReading
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing
from hubofhubs.the_world.science.interface import WorldKnowing
from hubofhubs.the_world.tools.web_search.interface import SearchBackend

LICENCES = ("MIT", "Apache-2.0", "Apache 2.0", "BSD-3-Clause", "BSD-2-Clause", "BSD", "ISC", "MPL-2.0", "LGPL", "AGPL", "GPL", "Unlicense", "CC-BY")
EXTRA_QUERIES = ("{q} alternatives", "{q} comparison", "{q} open source", "{q} documentation", "{q} maintained", "{q} licence", "{q} adoption", "{q} review")
MAX_RESULTS = 6
PROMPT_SCREEN = ("Question: {question}\nResults (id, title, snippet):\n{rows}\nReply with JSON only: {{\"drop\": [{{\"id\": \"i1\", \"reason\": \"short reason\"}}]}} "
                 "listing only results that do not bear on the question. Use no em dashes.")
PROMPT_SYNTH = ("Question: {question}\nDecision it informs: {decision}\nKept items (id, candidate, grade, claim):\n{rows}\nReply with JSON only: "
                "{{\"known\": \"...\", \"contested\": \"...\", \"unknown\": \"...\"}}, each one or two plain sentences from these items only. Use no em dashes.")


def as_hit(raw: Any) -> Dict[str, str]:
    """A search hit (a ``SearchHit`` or a mapping from The Science) as one flat mapping."""
    def get(*names: str) -> str:
        for name in names:
            value = raw.get(name) if isinstance(raw, Mapping) else getattr(raw, name, "")
            if value:
                return str(value)
        return ""
    return {"title": get("title"), "url": get("url", "link", "doi"), "snippet": get("snippet", "abstract", "text"), "date": get("date", "year"),
            "licence": get("licence", "license"), "relation": get("relation")}


def host_of(url: str) -> str:
    return (urlparse(url if "//" in url else "//" + url).hostname or "").removeprefix("www.")


def candidate_of(hit: Mapping[str, str], names: Sequence[str]) -> str:
    text = f"{hit['title']} {hit['snippet']}".lower()
    for name in names:
        if name.lower() in text:
            return name
    parsed = urlparse(hit["url"] if "//" in hit["url"] else "//" + hit["url"])
    segments = [s for s in parsed.path.split("/") if s]
    host = host_of(hit["url"])
    if host == "pypi.org" and len(segments) >= 2 and segments[0] == "project":
        return f"pypi/{segments[1]}"
    return f"{host}/{segments[0]}/{segments[1]}" if host == "github.com" and len(segments) >= 2 else (host or hit["title"][:40])


def licence_of(text: str) -> str:
    for name in LICENCES:
        if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", text):
            return name
    return ""


@implementation("the-learning", "systematic_review")
class SystematicReview:
    """Searches as a small systematic review and returns the investigation record; reports what is due."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, freshness: FreshnessReading, science: Lazy[WorldKnowing], web: Lazy[SearchBackend], plumbing: Lazy[ModelPlumbing],
                 tier: str = "fast", ask: Optional[Callable[[str], str]] = None):
        self.freshness, self.science, self.web, self.plumbing, self.tier, self.injected = freshness, science, web, plumbing, tier, ask

    # --- what is stale and what is due -------------------------------------------------------------------------------------------------
    def stale_areas(self, today: str = "") -> Sequence[str]:
        return investigation_store.stale_areas(self.freshness, today)

    def due_investigations(self, today: str = "", root: Any = None) -> Sequence[Mapping[str, Any]]:
        return investigation_store.due(today, root, self.freshness)

    def investigations_for(self, solution_id: str, include_ancestors: bool = True, today: str = "", root: Any = None) -> Sequence[Mapping[str, str]]:
        return investigation_store.investigations_for(solution_id, include_ancestors, today, root)

    def standing_schedule(self, last_run: str = "") -> Mapping[str, Any]:
        return investigation_store.standing_schedule(last_run)

    # --- the review --------------------------------------------------------------------------------------------------------------------
    def review(self, question: str, decision: str, weight: Any = None, size: str = "", links: Sequence[str] = (), criteria: Optional[Mapping[str, Any]] = None,
               candidates: Sequence[str] = (), queries: Sequence[str] = (), intent_id: str = "", experiment_id: str = "", today: str = "",
               refresh_days: Optional[int] = None, investigation_id: str = "", use_model: bool = False, solution_id: str = "", root: Any = None,
               reuse: bool = True) -> Mapping[str, Any]:
        size = size or inv.choose_size(weight)
        day = today or date.today().isoformat()
        links, filed = investigation_store.with_solution(links, solution_id)
        notes = ["no solution was given, so it is filed under the top solution " + filed["solution"]] if filed["fallback"] else []
        earlier = investigation_store.earlier_for(question, size, links, day, root) if reuse else None
        if earlier and earlier["state"] == "fresh":
            return {**investigation_store.record_of(earlier, root), "solution_link": filed}
        if earlier:
            notes.append(f"extends {earlier['investigation_id']} ({earlier['state']}: {'past its revisit date' if earlier['state'] == 'stale' else 'it was a smaller review'})")
        crit = {"include_terms": [], "exclude_terms": [], "since": "", "allow_undated": True, "licence_allow": [], "candidate_hosts": {}, **(criteria or {})}
        plan = self.plan(question, candidates, queries, size)
        kinds = list(inv.SOURCE_KINDS[size])
        protocol = {"protocol_date": day, "question": question, "decision": decision, "size": size, "criteria": crit, "queries": plan, "sources": kinds,
                    "candidates": list(candidates)}
        hits, log, limits = self.search(plan, kinds, day)
        kept, reasons = self.screen(hits, crit, candidates)
        found = len(hits)
        if use_model and kept:
            kept, dropped = self.judge(question, kept)
            for reason, n in dropped.items():
                reasons[reason] = reasons.get(reason, 0) + n
        items = self.extract(kept, candidates, crit, kinds, question, limits, size)
        known, contested, unknown = self.synthesise(items, crit, question, decision, use_model)
        decisions = self.decide(items, crit)
        if not items and limits and not found:
            decisions = ["all: defer: no results came back because a source failed, so nothing was judged, redo the review"]
        rid = investigation_id or self.new_id(day, intent_id, question)
        if earlier and rid == earlier["investigation_id"]:
            rid += "-extended"           # an extension is a new investigation that names the earlier one, never the same row
        applied = self.apply(items, decisions, links, rid)
        row = {"investigation_id": rid, "kind": "review", "intent_id": intent_id, "experiment_id": experiment_id, "links": inv.SEP.join(links), "question": question,
               "decision": decision, "size": size, "protocol_date": day, "method": f"{size} systematic review: protocol fixed on {day} before the first query; rules for screening, "
               "extraction and grading, results screened by criteria, kept items graded A to D", "criteria": self.criteria_text(crit), "sources": ", ".join(kinds),
               "queries": inv.SEP.join(f"{e['source']} | {e['query']} | {e['date']} | {e['hits']}" for e in log), "done_on": day, "found": str(found),
               "screened_out": inv.SEP.join(f"{n} {reason}" for reason, n in reasons.items()) or "0 nothing screened out", "kept": str(len(items)),
               "synthesis_known": known, "synthesis_contested": contested, "synthesis_unknown": unknown,
               "limitations": ", ".join([", ".join(limits) or "titles and result snippets only for items not opened"] + notes), "decisions": inv.SEP.join(decisions),
               "refresh_on": inv.refresh_on(day, size, refresh_days), "status": "open"}
        for column in inv.COLUMNS:
            row.setdefault(column, "")
        for item in items:
            item["investigation_id"] = rid
            item["applied"] = applied.get(item["item_id"], "")
        review = inv.Investigation(row=row, items=[{c: i.get(c, "") for c in inv.ITEM_COLUMNS} for i in items], protocol=protocol, log=log, reasons=reasons,
                           applied=[{"item": k, "applied": v} for k, v in applied.items()])
        return {**review.to_dict(), "solution_link": filed, "reused": False, "extends": earlier["investigation_id"] if earlier else ""}

    def new_id(self, day: str, intent_id: str, question: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", question.lower()).strip("-")[:32].strip("-")
        return f"r-{day}-{slug or 'review'}"

    def plan(self, question: str, candidates: Sequence[str], queries: Sequence[str], size: str) -> List[str]:
        """The queries, fixed before searching: those given, else the question and one per candidate, padded with variants to the size's count."""
        plan = list(dict.fromkeys(queries)) or [question] + [f"{c} licence maintained" for c in candidates]
        want = {"quick": 2, "standard": 5, "full": 8}[size]
        for template in EXTRA_QUERIES:
            if len(plan) >= want:
                break
            plan.append(template.format(q=question))
        return plan[:max(want, len(queries))][:inv.QUERIES[size] if not queries else len(queries)]

    def search(self, plan: Sequence[str], kinds: Sequence[str], day: str):
        hits: List[Dict[str, str]] = []
        log: List[Dict[str, Any]] = []
        limits: List[str] = []
        for query in plan:
            for kind in [k for k in kinds if k != "opened pages"]:
                found: List[Dict[str, str]] = []
                try:
                    if kind == "web search":
                        found = [as_hit(h) for h in self.web.search(query, max_results=MAX_RESULTS).hits]
                    else:
                        found = [as_hit(h) for h in self.science.search(query, max_results=MAX_RESULTS).hits]
                except Exception as error:    # a source that fails is a limitation, never a failed review
                    limits.append(f"{kind} failed for one query ({type(error).__name__})")
                log.append({"source": kind, "query": query, "date": day, "hits": len(found)})
                hits += [dict(h, found_by=kind) for h in found]
        return hits, log, list(dict.fromkeys(limits))

    def screen(self, hits: Sequence[Mapping[str, str]], crit: Mapping[str, Any], candidates: Sequence[str]):
        kept: List[Dict[str, str]] = []
        reasons: Dict[str, int] = {}
        seen = set()

        def out(reason: str) -> None:
            reasons[reason] = reasons.get(reason, 0) + 1
        for hit in hits:
            raw = f"{hit['title']} {hit['snippet']}"
            text = raw.lower()
            key = re.sub(r"[?#].*$", "", hit["url"].lower()).rstrip("/")
            if not hit["url"]:
                out("no source address")
            elif key in seen:
                out("duplicate of a kept result")
            elif any(t.lower() in text for t in crit["exclude_terms"]):
                out("matched an exclusion term")
            elif crit["include_terms"] and not any(t.lower() in text for t in crit["include_terms"]):
                out("matched no inclusion term")
            elif crit["since"] and hit["date"] and hit["date"][:10] < crit["since"]:
                out(f"older than {crit['since']}")
            elif crit["since"] and not hit["date"] and not crit["allow_undated"]:
                out("undated")
            elif crit["licence_allow"] and (lic := hit["licence"] or licence_of(raw)) and lic not in crit["licence_allow"]:
                out(f"licence {lic} not allowed")
            else:
                seen.add(key)
                kept.append(dict(hit))
        return kept, reasons

    def extract(self, kept: Sequence[Dict[str, str]], names: Sequence[str], crit: Mapping[str, Any], kinds: Sequence[str], question: str, limits: List[str], size: str = "standard"):
        by_candidate: Dict[str, List[Dict[str, str]]] = {}
        for hit in kept:
            hit["candidate"] = candidate_of(hit, names)
            own = [h.lower() for h in (crit["candidate_hosts"].get(hit["candidate"]) or ())]
            hit["independent"] = "unknown" if not hit["url"] else "no" if hit["relation"] in ("vendor", "maintainer") or host_of(hit["url"]) in own else "yes"
            by_candidate.setdefault(hit["candidate"], []).append(hit)
        budget = inv.OPEN_LIMIT[size] if "opened pages" in kinds else 0
        first, rest = [], []                                   # one page per candidate is opened before a second of any candidate
        seen_names = set()
        for n, hit in enumerate(kept):
            (rest if hit["candidate"] in seen_names else first).append(n)
            seen_names.add(hit["candidate"])
        pages: Dict[int, str] = {}
        for n in (first + rest)[:budget] if budget else []:
            try:
                page = self.science.fetch(kept[n]["url"], focus=question)
                if getattr(page, "kind", "") != "error" and getattr(page, "text", ""):
                    pages[n] = str(page.text)[:4000]
                elif "a page could not be opened" not in limits:
                    limits.append("a page could not be opened")
            except Exception:
                if "a page could not be opened" not in limits:
                    limits.append("a page could not be opened")
        items = []
        for n, hit in enumerate(kept, 1):
            sources = [{"independent": h["independent"], "relation": h["relation"], "host": host_of(h["url"])} for h in by_candidate[hit["candidate"]]]
            distinct = {s["host"] for s in sources if s["independent"] == "yes"}
            sources = [s for s in sources if s["independent"] != "yes"] + [{"independent": "yes", "relation": "", "host": h} for h in distinct]
            verified, text = "snippet", f"{hit['title']} {hit['snippet']}"
            if n - 1 in pages:
                verified, text = "opened", text + " " + pages[n - 1]
                if len(distinct) >= 2:
                    verified = "cross-checked"
            claim = " ".join((hit["snippet"] or hit["title"]).split())
            items.append({"item_id": f"i{n}", "candidate": hit["candidate"], "claim": claim[:300], "source": hit["url"], "source_date": hit["date"][:10] or "undated",
                          "independent": hit["independent"], "verified": verified, "licence": hit["licence"] or licence_of(text) or "unknown",
                          "grade": inv.cap_grade(inv.grade(sources), verified, size), "knowledge_id": "", "text": text.lower()})
        snippets = sum(1 for i in items if i["verified"] == "snippet")
        if snippets and size != "quick":
            limits.append(f"{snippets} kept item(s) read as result snippets only, graded C at most")
        elif snippets and "titles and result snippets only for items not opened" not in limits:
            limits.append("titles and result snippets only for items not opened")
        return items

    def synthesise(self, items: Sequence[Mapping[str, Any]], crit: Mapping[str, Any], question: str, decision: str, use_model: bool):
        by: Dict[str, List[Mapping[str, Any]]] = {}
        for i in items:
            by.setdefault(i["candidate"], []).append(i)
        known = [c for c, v in by.items() if any(i["grade"] in ("A", "B") for i in v)]
        contested = [c for c, v in by.items() if any(n in i["text"] for i in v for n in inv.NEGATIVE) and any(not any(n in i["text"] for n in inv.NEGATIVE) for i in v)]
        unknown = [f"{c} (grade {max(i['grade'] for i in v)} at best)" for c, v in by.items() if all(i["grade"] in ("C", "D") for i in v)]
        unknown += [f"licence of {c}" for c, v in by.items() if all(i["licence"] == "unknown" for i in v)]
        synthesis = (("Supported by a graded source: " + ", ".join(known)) if known else "Nothing reached grade B or better.",
                     ("Sources disagree on whether these are maintained: " + ", ".join(contested)) if contested else "No disagreement between kept sources.",
                     ("Not established: " + "; ".join(unknown)) if unknown else "Nothing left unestablished among the kept items.")
        if use_model and items:
            rows = "\n".join(f"{i['item_id']}, {i['candidate']}, {i['grade']}, {i['claim'][:160]}" for i in items)
            raw = self.say(PROMPT_SYNTH.format(question=question, decision=decision, rows=rows))
            data = load_json(raw)
            if all(isinstance(data.get(k), str) and data[k].strip() for k in ("known", "contested", "unknown")):
                synthesis = tuple(data[k].strip().replace(chr(0x2014), ",") for k in ("known", "contested", "unknown"))
        return synthesis

    def decide(self, items: Sequence[Mapping[str, Any]], crit: Mapping[str, Any]) -> List[str]:
        if not items:
            return ["all: no-candidate: no result passed the criteria"]
        by: Dict[str, List[Mapping[str, Any]]] = {}
        for i in items:
            by.setdefault(i["candidate"], []).append(i)
        out = []
        for name, group in by.items():
            best = min(i["grade"] for i in group)
            licence = next((i["licence"] for i in group if i["licence"] != "unknown"), "unknown")
            negative = any(n in i["text"] for i in group for n in inv.NEGATIVE) and all(any(n in i["text"] for n in inv.NEGATIVE) for i in group)
            if negative:
                out.append(f"{name}: reject: every kept source reports it archived, deprecated or unmaintained")
            elif crit["licence_allow"] and licence != "unknown" and licence not in crit["licence_allow"]:
                out.append(f"{name}: reject: licence {licence} is not allowed")
            elif best in ("A", "B") and licence != "unknown":
                out.append(f"{name}: adopt: grade {best} with licence {licence}")
            else:
                out.append(f"{name}: defer: " + ("licence unconfirmed" if licence == "unknown" else f"best grade {best}") + ", needs an independent source or a read of the page")
        return out

    def apply(self, items: Sequence[Dict[str, Any]], decisions: Sequence[str], links: Sequence[str], rid: str) -> Dict[str, str]:
        verdict = {d.split(":")[0].strip(): d.split(":")[1].strip() for d in decisions if d.count(":") >= 2}
        solution = next((link.split(":", 1)[1] for link in links if link.startswith("solution:")), "") or "intent"
        out = {}
        for n, item in enumerate(items, 1):
            what = verdict.get(item["candidate"], "")
            if what in ("adopt", "adapt", "build-on") and item["grade"] in ("A", "B"):
                out[item["item_id"]] = f"knowledge:k-{solution}-{rid}-{n}"
            else:
                out[item["item_id"]] = f"not-applied: candidate {what or 'unjudged'}, grade {item['grade']}"
        return out

    def criteria_text(self, crit: Mapping[str, Any]) -> str:
        bits = [f"include terms: {', '.join(crit['include_terms'])}" if crit["include_terms"] else "include: any result with a source address",
                f"exclude terms: {', '.join(crit['exclude_terms'])}" if crit["exclude_terms"] else "exclude: duplicates",
                f"since {crit['since']}" if crit["since"] else "any date",
                f"licences allowed: {', '.join(crit['licence_allow'])}" if crit["licence_allow"] else "any licence, recorded"]
        return "; ".join(bits).replace(";", ",")

    def judge(self, question: str, kept: Sequence[Dict[str, str]]):
        rows = "\n".join(f"i{n}, {h['title'][:80]}, {h['snippet'][:160]}" for n, h in enumerate(kept, 1))
        data = load_json(self.say(PROMPT_SCREEN.format(question=question, rows=rows)))
        drop = {str(d.get("id")) for d in data.get("drop", []) if isinstance(d, Mapping)} if isinstance(data.get("drop"), list) else set()
        keep = [h for n, h in enumerate(kept, 1) if f"i{n}" not in drop]
        return keep, ({"judged not to bear on the question": len(kept) - len(keep)} if len(keep) != len(kept) else {})

    def say(self, prompt: str) -> str:
        try:
            return self.injected(prompt) if self.injected is not None else self.plumbing.ask(prompt, self.tier)
        except Exception:
            return ""


def load_json(raw: str) -> Dict[str, Any]:
    found = re.search(r"\{.*\}", raw or "", re.S)
    try:
        data = json.loads(found.group(0)) if found else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
