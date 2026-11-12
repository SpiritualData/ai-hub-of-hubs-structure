"""Writes cases.json: scenarios of fixed fake search results for recorded and reused research, each checked on structured facts read from the stores after the run.
Run: python3 evaluation/research_recorded/build_cases.py. The fixtures are neutral (terminal libraries) and the same search results serve every case."""
import json
from pathlib import Path

shared = json.loads((Path(__file__).resolve().parent.parent / "learning_review" / "cases.json").read_text())[0]["args"]      # the search results and criteria the Learning review cases use
CRITERIA, NAMES, SCIENCE, WEB = shared["review"]["criteria"], shared["review"]["candidates"], shared["science"], shared["web"]

BASE = dict(question="which terminal UI libraries are adoptable", decision="adopt, adapt or build", intent_id="terminal", today="2026-11-10", criteria=CRITERIA,
            candidates=NAMES, weight="standard")
RELATED = dict(question="is there a maintained Python library for drawing a terminal screen", decision="pick the library the terminal arm uses")
OTHER = dict(question="which password manager has an open audit", decision="pick one for the team")


def case(cid, area, check, expect, review=None, **extra):
    args = {"check": check, "web": WEB, "science": SCIENCE, "review": dict(BASE, **(review or {})), "places": ["sol-a"], **extra}
    return {"id": cid, "area": area, "kind": check, "args": args, "expect": expect}


FRESH = dict(prior={}, judge_says="")
PRIOR_ON_A = dict(prior_links=["solution:sol-a"])

cases = [
    case("first-complete-standard", "first", "first", {"complete": True, "linked": "sol-a", "stored": 1, "knowledge_on": ["sol-a"], "context": 1}),
    case("first-complete-quick", "first", "first", {"complete": True, "linked": "sol-a", "stored": 1, "knowledge_on": ["sol-a"], "context": 1}, review=dict(weight="quick")),
    case("reuse-same-question", "reuse", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1}, prior={}, **PRIOR_ON_A),
    case("reuse-related-question", "reuse", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1}, review=RELATED, prior={}, judge_says="prior", **PRIOR_ON_A),
    case("reuse-in-the-same-scope", "reuse", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1},
         review=dict(links=["scope:quest-a"]), prior={}, prior_links=["solution:sol-a", "scope:quest-a"]),
    case("stale-is-extended-in-place", "extend", "extend", {"reused": False, "updated": True, "rows": 1, "same_id": True, "items_grew": True, "searched": True},
         prior={}, prior_refresh_on="2026-10-01", **PRIOR_ON_A),
    case("smaller-is-extended-in-place", "extend", "extend", {"reused": False, "updated": True, "rows": 1, "same_id": True, "items_grew": True, "searched": True},
         prior=dict(weight="quick"), **PRIOR_ON_A),
    case("unrelated-is-not-pulled", "unrelated", "unrelated", {"reused": False, "searched": True, "prior_untouched": True}, review=OTHER, prior={}, places=["sol-b"], **PRIOR_ON_A),
    case("unrelated-is-recorded-on-its-own-solution", "unrelated", "unrelated_recorded", {"rows": 1, "linked": "sol-b"}, review=OTHER, places=["sol-b"]),
    case("a-quick-fact-is-not-burdened", "quick", "quick", {"rows": 0, "knowledge": 0, "context": 0, "small": True}, review=dict(decision="", weight=None)),
    case("a-finding-becomes-knowledge-once", "knowledge", "knowledge_once", {"knowledge": True, "duplicates": 0}),
    case("a-person's-own-knowledge-is-kept", "knowledge", "owner_text", {"owner_row_intact": True, "knowledge": True}),
    case("a-fenced-investigation-stays-in-its-scope", "scope", "scope", {"reused": False, "searched": True, "context_scope": ["quest-b"]},
         review=dict(links=["scope:quest-b"]), prior={}, prior_links=["solution:sol-a", "scope:quest-a"]),
    case("a-held-knowledge-item-still-records-the-investigation", "gate", "held", {"rows": 1, "held_cells": True, "complete": True}, knowledge_held=True),
    case("a-failing-store-never-fails-the-answer", "gate", "store_down", {"answered": True, "recorded": False, "said": True}, store_down=True),
    case("first-complete-full", "first", "first", {"complete": True, "linked": "sol-a", "stored": 1, "knowledge_on": ["sol-a"], "context": 1}, review=dict(weight="full")),
    case("first-on-the-solution-it-serves", "first", "first", {"complete": True, "linked": "sol-b", "stored": 1, "knowledge_on": ["sol-b"], "context": 1}, places=["sol-b"]),
    case("first-on-the-solution-the-caller-names", "first", "first", {"complete": True, "linked": "sol-b", "stored": 1, "knowledge_on": ["sol-b"], "context": 1},
         review=dict(links=["solution:sol-b"]), places=["sol-a"]),
    case("reuse-with-the-solution-named", "reuse", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1}, review=dict(links=["solution:sol-a"]), prior={}, **PRIOR_ON_A),
    case("reuse-ignores-case-and-spacing", "reuse", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1},
         review=dict(question="  Which TERMINAL UI libraries   are adoptable "), prior={}, **PRIOR_ON_A),
    case("reuse-a-larger-one-for-a-smaller-ask", "reuse", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1}, review=dict(weight="quick"), prior={}, **PRIOR_ON_A),
    case("a-related-question-the-judge-declines-is-researched", "unrelated", "unrelated", {"reused": False, "searched": True, "prior_untouched": True},
         review=RELATED, prior={}, judge_says="", **PRIOR_ON_A),
    case("stale-related-question-is-extended-in-place", "extend", "extend", {"reused": False, "updated": True, "rows": 1, "same_id": True, "items_grew": True, "searched": True},
         review=RELATED, prior={}, prior_refresh_on="2026-10-01", judge_says="prior", **PRIOR_ON_A),
    case("an-unfenced-investigation-is-seen-by-a-fenced-request", "scope", "reuse", {"reused": True, "searches": 0, "cited": "2026-11-10", "rows": 1},
         review=dict(links=["scope:quest-b"]), prior={}, **PRIOR_ON_A),
    case("a-fenced-investigation-is-hidden-from-an-unfenced-request", "scope", "scope", {"reused": False, "searched": True, "context_scope": []},
         prior={}, prior_links=["solution:sol-a", "scope:quest-a"]),
    case("a-held-knowledge-item-still-extends-the-investigation", "gate", "held", {"rows": 1, "held_cells": True, "complete": True}, knowledge_held=True,
         prior={}, prior_refresh_on="2026-10-01", **PRIOR_ON_A),
    case("a-person's-own-knowledge-is-kept-when-extending", "knowledge", "owner_text", {"owner_row_intact": True, "knowledge": True}, prior={}, prior_refresh_on="2026-10-01", **PRIOR_ON_A),
    case("a-quick-fact-with-a-big-weight-is-still-light", "quick", "quick", {"rows": 0, "knowledge": 0, "context": 0, "small": True}, review=dict(decision="", weight="standard")),
    case("the-same-question-asked-twice-is-researched-once", "reuse", "twice", {"reused": True, "rows": 1}),
    case("recorded-from-a-turns-own-reads", "observed", "observed",
         {"rows": 1, "searches": 0, "complete": True, "queries_kept": 2, "queries_logged": 2, "discipline": True, "from_the_answer": True, "revisit_days": 14, "knowledge": True, "context": 1},
         observed=[{"query": "terminal UI libraries for python", "hits": WEB[:5]}, {"query": "termlib maintained", "hits": WEB[5:9]}], answer="termlib is the usual choice and is maintained.",
         source_criteria="independent reviews and the project's own page", would_change="a maintained rival under a permissive licence"),
    case("a-quick-fact-from-a-turn-records-nothing", "observed", "observed_quick", {"rows": 0, "knowledge": 0, "context": 0, "recorded": False}, review=dict(decision=""),
         observed=[{"query": "terminal UI libraries for python", "hits": WEB[:5]}], answer="termlib."),
    case("a-repeat-from-a-turn-does-not-duplicate", "observed", "observed_twice", {"rows": 1, "reused": True, "searches": 0},
         observed=[{"query": "terminal UI libraries for python", "hits": WEB[:5]}], answer="termlib is the usual choice.", source_criteria="independent reviews", would_change="a rival"),
    case("a-quick-fact-after-an-investigation-is-not-pulled", "quick", "quick", {"rows": 1, "knowledge": 0, "context": 0, "small": True}, review=dict(decision="", weight=None),
         prior={}, **PRIOR_ON_A),
]
for c in cases:
    if "prior" in c["args"]:       # the earlier investigation: the base question at the same size as the new one unless the case says smaller
        c["args"]["prior"] = {"question": BASE["question"], "decision": BASE["decision"], "weight": "standard", **c["args"]["prior"]}

Path(__file__).with_name("cases.json").write_text(json.dumps(cases, indent=1) + "\n")
print(len(cases), "cases")
