"""Writes cases.json: scenarios of fixed fake search results, each checked on one property of the review record. Run: python3 evaluation/learning_review/build_cases.py"""
import json
from pathlib import Path

WEB = [
    {"title": "termlib", "url": "https://github.com/acme/termlib", "snippet": "termlib is a MIT licensed terminal UI library for Python", "date": "2026-09-01"},
    {"title": "termlib review", "url": "https://blog.example.org/termlib", "snippet": "An independent review of termlib: stable and widely used", "date": "2026-08-01"},
    {"title": "termlib", "url": "https://github.com/acme/termlib", "snippet": "duplicate of the first hit", "date": "2026-09-01"},
    {"title": "oldkit", "url": "https://github.com/acme/oldkit", "snippet": "oldkit is archived and deprecated, Apache-2.0", "date": "2026-02-01"},
    {"title": "gplkit", "url": "https://github.com/acme/gplkit", "snippet": "gplkit terminal library under the GPL", "date": "2026-07-01"},
    {"title": "cooking", "url": "https://example.org/pasta", "snippet": "pasta recipes with no relation", "date": "2026-07-01"},
    {"title": "stale", "url": "https://example.org/stale", "snippet": "an old terminal library note", "date": "2020-01-01"},
    {"title": "nosource", "url": "", "snippet": "a result with no address", "date": ""},
    {"title": "vendorkit", "url": "https://vendorkit.example.com/", "snippet": "vendorkit, the fastest terminal library, says its own page", "date": "2026-10-01"},
]
SCIENCE = [{"title": "A study of terminal UIs", "url": "https://papers.example.org/tui", "abstract": "terminal UI study, library comparison", "year": "2026"}]
NAMES = ["termlib", "oldkit", "gplkit", "vendorkit"]
CRITERIA = {"exclude_terms": ["recipes"], "since": "2026-01-01", "licence_allow": ["MIT", "Apache-2.0"], "candidate_hosts": {"vendorkit": ["vendorkit.example.com"]}}
BASE = dict(question="which terminal UI libraries are adoptable", decision="adopt, adapt or build", intent_id="terminal", today="2026-11-10",
            links=["solution:terminal-experience"], criteria=CRITERIA, candidates=NAMES)


def case(cid, area, check, weight, expect, **extra):
    args = {"check": check, "web": WEB, "science": SCIENCE, "review": dict(BASE, weight=weight, **extra.pop("review", {})), **extra}
    return {"id": cid, "area": area, "kind": check, "args": args, "expect": expect}


cases = [
    case("complete-quick", "parts", "complete", "quick", []),
    case("complete-standard", "parts", "complete", "standard", []),
    case("complete-full", "parts", "complete", "full", []),
    case("protocol-first", "parts", "protocol_first", "standard", True),
    case("queries-standard", "parts", "queries_min", "standard", True, minimum=5),
    case("queries-full", "parts", "queries_min", "full", True, minimum=8),
    case("size-selects", "size", "size", {"selects": True}, "standard"),
    case("size-outward", "size", "size", {"outward": True}, "full"),
    case("size-quick", "size", "size", {"reversible_days": 0.5}, "quick"),
    case("exclusions-reasoned", "exclusions", "exclusions", "quick",
         {"duplicate of a kept result": 3 * 2, "no source address": 2 * 1, "matched an exclusion term": 2 * 1, "older than 2026-01-01": 2 * 1,
          "licence GPL not allowed": 2 * 1}),
    case("exclusions-add-up", "exclusions", "exclusions_add_up", "standard", True),
    case("grades-by-rule", "grades", "grades", "quick", {"termlib": "A", "oldkit": "B", "vendorkit": "D"}),
    case("standard-opens-kept-pages", "verification", "verified", "standard", {"termlib": "cross-checked", "oldkit": "snippet", "gplkit": "opened", "vendorkit": "snippet"},
         review={"criteria": dict(CRITERIA, since="", licence_allow=[])}),
    case("snippet-never-above-c-standard", "verification", "no_high_grade_on_snippet", "standard", True, review={"criteria": dict(CRITERIA, since="", licence_allow=[])}),
    case("snippet-never-above-c-full", "verification", "no_high_grade_on_snippet", "full", True, review={"criteria": dict(CRITERIA, since="", licence_allow=[])}),
    case("snippet-graded-c-at-standard", "verification", "grades", "standard", {"termlib": "A", "oldkit": "C", "gplkit": "B", "vendorkit": "D"},
         review={"criteria": dict(CRITERIA, since="", licence_allow=[])}),
    case("quick-stays-on-snippets", "verification", "verified", "quick", {"termlib": "snippet", "oldkit": "snippet", "vendorkit": "snippet"}),
    case("unknowns-stated", "synthesis", "unknowns", "standard", True),
    case("decision-per-candidate", "decisions", "decisions", "quick", {"termlib": "adopt", "oldkit": "reject", "vendorkit": "defer"}),
    case("decision-none-found", "decisions", "decisions", "quick", {"all": "no-candidate"}, review={"criteria": {"include_terms": ["nothing-matches"]}}),
    case("applied-present", "applied", "applied", "standard", True),
    case("refresh-quick", "refresh", "refresh", "quick", "2026-12-10"),
    case("refresh-standard", "refresh", "refresh", "standard", "2027-02-08"),
    case("refresh-full", "refresh", "refresh", "full", "2027-05-09"),
]
REAL = [("real-terminal-libraries", "Which open-source terminal agent libraries are adoptable for a Python terminal UI?", "adopt an existing library as an arm, or write one", "terminal-experience"),
        ("real-search-backends", "Which open-source web search backends can run without a vendor key?", "adopt one as an arm, or keep the current ones", "web-search"),
        ("real-spreadsheet-libraries", "Which Python libraries read and write spreadsheet files without a vendor service?", "adopt one as an arm, or write a reader", "file-reading")]
for cid, question, decision, solution in REAL:
    cases.append({"id": cid, "area": "real", "kind": "real", "args": {"question": question, "decision": decision, "solution": solution},
                  "expect": {"complete": True, "found_results": True, "kept_some": True, "every_candidate_decided": True, "no_high_grade_on_unread": True}})
Path(__file__).with_name("cases.json").write_text(json.dumps(cases, indent=1) + "\n")
print(len(cases), "cases")
