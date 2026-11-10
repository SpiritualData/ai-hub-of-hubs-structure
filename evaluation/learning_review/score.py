"""Scores a Learning arm on the knowledge search standard: given fixed fake search results (no network, no model), does the investigation record (a review) have every part of its size,
are exclusions counted and reasoned, are grades applied by the rule, are unknowns stated, does every candidate have a decision, is the applied part present and the
revisit date set? One number: the share of cases passed. Each case runs one scenario and checks one property of the record."""
import inspect
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

from hubofhubs.the_world.learning import investigation_store  # noqa: E402
from hubofhubs.the_world.learning.research_freshness_reader.registry import RegistryScan  # noqa: E402
from hubofhubs.the_world.learning.systematic_review import SystematicReview  # noqa: E402
from hubofhubs.the_world.observation import Observation  # noqa: E402
from hubofhubs.the_world.tools.web_search.search_port import SearchHit, SearchResponse  # noqa: E402


class FakeWeb:
    def __init__(self, hits):
        self.hits = hits

    def search(self, query, *, max_results=5, instruction=None):
        return SearchResponse(hits=[SearchHit(h["title"], h["url"], h.get("snippet", ""), h.get("date", "")) for h in self.hits])


class FakeScience:
    def __init__(self, hits):
        self.hits = hits

    def search(self, queries, *, max_results=None, fresh=False):
        return Observation(kind="query", text="", hits=list(self.hits))

    def fetch(self, url, *, focus=None, fresh=False, full=False, part=None):
        if "oldkit" in url or "vendorkit" in url:      # these pages cannot be opened in the scripted cases, so their items stay snippets
            return Observation(kind="error", error="not opened in the scripted cases")
        return Observation(kind="read", text="The page text says the library is maintained.")


def facts(record, args):
    """The property of the record a case checks."""
    row, items = record["investigation"], record["items"]
    decisions = {d.split(":")[0].strip(): d.split(":")[1].strip() for d in row["decisions"].split(";") if d.count(":") >= 2}
    checks = {
        "complete": lambda: record["gaps"],
        "size": lambda: row["size"],
        "protocol_first": lambda: row["protocol_date"] <= row["done_on"] and bool(row["criteria"]) and all(q.count("|") == 3 for q in row["queries"].split(";")),
        "queries_min": lambda: len(row["queries"].split(";")) >= args["minimum"],
        "exclusions": lambda: record["screened_out"],
        "exclusions_add_up": lambda: int(row["found"]) - sum(record["screened_out"].values()) == int(row["kept"]) == len(items),
        "grades": lambda: {n: next(i["grade"] for i in items if n in i["claim"].lower()) for n in args["review"]["candidates"] if any(n in i["claim"].lower() for i in items)},
        "verified": lambda: {n: next(i["verified"] for i in items if n in i["claim"].lower()) for n in args["review"]["candidates"] if any(n in i["claim"].lower() for i in items)},
        "no_high_grade_on_snippet": lambda: not any(i["verified"] == "snippet" and i["grade"] in ("A", "B") for i in items),
        "unknowns": lambda: bool(row["synthesis_unknown"]) and bool(row["synthesis_contested"]) and bool(row["synthesis_known"]),
        "decisions": lambda: decisions,
        "applied": lambda: all(i["applied"] and (i["applied"].startswith("knowledge:") or i["applied"].startswith("not-applied: ")) for i in items),
        "refresh": lambda: row["refresh_on"],
        "solution_link": lambda: {"links": [l for l in row["links"].split(";") if l.startswith("solution:")], "fallback": record["solution_link"]["fallback"],
                                  "recorded": "top solution" in row["limitations"]},
        "reuse": lambda: {"reused": record["reused"], "searched": bool(record["queries"]) and not record["reused"], "same_record": row["investigation_id"] == args["prior_id"],
                          "extends": record["extends"] == args["prior_id"]},
    }
    return checks[args["check"]]()


REAL = "real-"      # ids of the real reviews (the small stage); they run only when named with ``--only`` and a call budget, never in the scripted run


def load_cases():
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    return cases if "--only" in sys.argv else [c for c in cases if c["kind"] != "real"]


def real_review(args, meter):
    """One real quick review through the assembled hub on a plain install (a logged-in Claude CLI, no vendor key); every search and model call is metered."""
    from hubofhubs.api import AssemblyConfig, assemble
    system = assemble(config=AssemblyConfig(solutions=("the-learning", "model-plumbing"), names={"the-learning": "systematic_review", "web-search": "claude_login", "vendor-model-caller": "claude_cli"}))
    arm = system["the-learning"]
    plumbing = system["model-plumbing"]

    def ask(prompt):
        meter.record()
        return plumbing.ask(prompt, "fast")
    arm.injected = ask
    got = arm.review(args["question"], args["decision"], weight="quick", intent_id="the-world", links=["solution:" + args["solution"]], use_model=True,
                     criteria={"since": "2025-01-01"})
    for _ in got["queries"]:
        meter.record()                      # each logged web search is one call of the Claude login arm
    row, items = got["investigation"], got["items"]
    decisions = [d for d in row["decisions"].split(";") if d.strip()]
    return {"complete": got["gaps"] == [], "found_results": int(row["found"]) > 0, "kept_some": len(items) > 0,
            "every_candidate_decided": bool(decisions) and all(d.count(":") >= 2 and d.split(":")[1].strip() in ("adopt", "adapt", "build-on", "reject", "defer", "no-candidate") for d in decisions), "no_high_grade_on_unread": not any(i["verified"] == "snippet" and i["grade"] in ("A", "B") and row["size"] != "quick" for i in items)}


def adapt(implementation, meter):
    def run(kind, args):
        if kind == "real":
            return real_review(args, meter)
        seats = dict(freshness=RegistryScan(), science=FakeScience(args.get("science", [])), web=FakeWeb(args.get("web", [])), plumbing=None)
        arm = implementation(**{k: v for k, v in seats.items() if k in inspect.signature(implementation).parameters})
        with tempfile.TemporaryDirectory() as root:      # the store the arm looks earlier investigations up in: empty, or holding the case's one earlier investigation
            if args.get("prior"):
                made = SystematicReview(**seats).review(**dict(args["review"], **args["prior"], root=root, reuse=False))
                investigation_store.store(made, Path(root) / "hubofhubs" / "registry")
                args = dict(args, prior_id=made["investigation"]["investigation_id"])
            record = arm.review(**dict(args["review"], root=root))
            return facts(record, args)
    return run


def score_case(fn, case):
    try:
        return judge(fn(case["kind"], case["args"]), case)
    except Exception as error:       # an arm that cannot produce the record fails the case
        return dict(ok=False, got=type(error).__name__, note=str(error)[:80])
