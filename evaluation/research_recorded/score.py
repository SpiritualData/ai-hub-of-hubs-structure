"""Scores a Learning arm on recorded and reused research: does a first question leave a complete investigation linked to the right solution, with its knowledge items
and one context item; does a related question in a fresh conversation find it and reuse it with no search; does a stale or smaller one have only its gap searched and the same
investigation updated in place; is an unrelated question left alone; is a quick fact not burdened; does a finding become a knowledge item once and never over a person's
text; does a fenced investigation stay in its scope; does a record the structure holds for a person still get recorded; does a failing store leave the answer intact.

Everything is fixed fake search results and a scripted judge (no network, no model). Each case checks one property as structured facts read from the stores after the run
(the investigation files, the knowledge files, the context items) and the counted searches, never from the arm's own claims about itself. The score is the share of cases
passed (each case weighs the same; fixed before any arm was scored, in README.md). ``searches`` per arm on the reuse cases is the cost the metric reports."""
import csv
import inspect
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

from learning_review.score import FakeScience, FakeWeb  # noqa: E402
from hubofhubs.the_world.learning import investigation_store  # noqa: E402
from hubofhubs.the_world.learning.research_freshness_reader.registry import RegistryScan  # noqa: E402
from hubofhubs.the_world.learning.research_ports import FolderKnowledge, FolderStore  # noqa: E402
from hubofhubs.the_world.learning.systematic_review import SystematicReview  # noqa: E402


class Counting:
    """A search seat that counts the searches made through it."""

    def __init__(self, inner):
        self.inner, self.calls = inner, 0

    def search(self, *args, **kwargs):
        self.calls += 1
        return self.inner.search(*args, **kwargs)

    def fetch(self, *args, **kwargs):
        return self.inner.fetch(*args, **kwargs)


class Context:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(dict(item))


class HoldingKnowledge:
    """A knowledge location that holds every change for a person (the write gate of a consumer whose structure the AI may not write)."""

    def add(self, solution_ids, claim, source, knowledge_id, investigation_id, kind="evidence", recorded=""):
        return {"status": "proposed", "reason": "waiting for the owner"}


class BrokenStore(FolderStore):
    def write(self, spec):
        raise RuntimeError("the store is down")


def table(path):
    if not path.exists():
        return []
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def seed(root):
    """Two solutions of the records under ``root``, each with a folder (so a knowledge item has a place), and a person's own knowledge row on the first."""
    for name, sid in (("a", "sol-a"), ("b", "sol-b")):
        folder = Path(root) / "hubofhubs" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "solutions.csv").write_text(f"solution_id\n{sid}\n")
    (Path(root) / "hubofhubs" / "a" / "knowledge.csv").write_text(
        "knowledge_id,claim,kind,source,solution_ids,status,status_by,recorded,expiration,investigation_id\n"
        "k-person-1,A person's own assumption about the terminal.,best guess,the owner,sol-a,active,,2026-10-01,,\n")


def knowledge_rows(root):
    return [r for name in ("a", "b") for r in table(Path(root) / "hubofhubs" / name / "knowledge.csv") if r["knowledge_id"] != "k-person-1"]


def facts(check, args, root, record, searches, context, prior, ids):
    rows = table(Path(root) / "hubofhubs" / "registry" / "investigations.csv")
    items = table(Path(root) / "hubofhubs" / "registry" / "investigation_items.csv")
    know = knowledge_rows(root)
    row = record.get("investigation") or {}
    linked = [link[9:] for link in row.get("links", "").split(";") if link.startswith("solution:")]
    claims = [(k["claim"], k["solution_ids"]) for k in know]
    checks = {
        "first": lambda: {"complete": record["gaps"] == [], "linked": linked[0] if linked else "", "stored": len(rows), "knowledge_on": sorted({k["solution_ids"] for k in know}),
                          "context": len(context.items)},
        "reuse": lambda: {"reused": record["reused"], "searches": searches, "cited": (record.get("cited") or {}).get("done_on", ""), "rows": len(rows)},
        "twice": lambda: {"reused": record["reused"], "rows": len(rows)},
        "extend": lambda: {"reused": record["reused"], "updated": record.get("updated", False), "rows": len(rows), "same_id": bool(rows) and rows[0]["investigation_id"] == prior["id"],
                           "items_grew": len(items) > prior["items"], "searched": searches > 0},
        "unrelated": lambda: {"reused": record["reused"], "searched": searches > 0, "prior_untouched": bool(rows) and rows[0]["synthesis_known"] == prior["known"] and rows[0]["done_on"] == prior["done_on"]},
        "unrelated_recorded": lambda: {"rows": len(rows), "linked": linked[0] if linked else ""},
        "quick": lambda: {"rows": len(rows), "knowledge": len(know), "context": len(context.items), "small": len(record["queries"]) <= 2},
        "knowledge_once": lambda: {"knowledge": len(know) > 0, "duplicates": len(claims) - len(set(claims))},
        "owner_text": lambda: {"owner_row_intact": any(r["knowledge_id"] == "k-person-1" and r["claim"] == "A person's own assumption about the terminal."
                                                       for r in table(Path(root) / "hubofhubs" / "a" / "knowledge.csv")), "knowledge": len(know) > 0},
        "scope": lambda: {"reused": record["reused"], "searched": searches > 0, "context_scope": context.items[0]["scope"] if context.items else []},
        "held": lambda: {"rows": len(rows), "held_cells": bool(items) and all(i["applied"].startswith("not-applied") or i["applied"] == "" for i in items), "complete": record["gaps"] == []},
        "store_down": lambda: {"answered": bool(record.get("items")), "recorded": record.get("recorded", None), "said": bool(record.get("record_error"))},
    }
    return checks[check]()


def adapt(implementation, meter):
    def run(kind, args):
        with tempfile.TemporaryDirectory() as root:
            seed(root)
            web, science = Counting(FakeWeb(args["web"])), Counting(FakeScience(args.get("science", [])))
            store = (BrokenStore if args.get("store_down") else FolderStore)(root)
            context = Context()
            prior = {}
            ids = {}
            if args.get("prior"):          # an earlier investigation, written the way a consumer's store holds it
                spec = dict(args["review"], **args["prior"], root=root, reuse=False)
                made = SystematicReview(freshness=RegistryScan(), science=Counting(FakeScience(args.get("science", []))), web=Counting(FakeWeb(args["web"])), plumbing=None).review(**spec)
                row = dict(made["investigation"])
                if args.get("prior_refresh_on"):
                    row["refresh_on"] = args["prior_refresh_on"]
                row["links"] = ";".join(args["prior_links"]) if args.get("prior_links") else row["links"]
                FolderStore(root).write({"investigation": row, "items": made["items"]})
                prior = {"id": row["investigation_id"], "items": len(made["items"]), "known": row["synthesis_known"], "done_on": row["done_on"]}

            def ask(prompt):
                return json.dumps({"answered_by": prior.get("id", "") if args.get("judge_says") == "prior" else ""})
            ports = dict(freshness=RegistryScan(), science=science, web=web, plumbing=None, ask=ask, store=store, context=context,
                         knowledge=HoldingKnowledge() if args.get("knowledge_held") else FolderKnowledge(root),
                         placer=lambda question, decision: list(args.get("places", [])))
            arm = implementation(**{k: v for k, v in ports.items() if k in inspect.signature(implementation).parameters})
            for _ in range(2 if args["check"] in ("knowledge_once", "twice") else 1):
                record = arm.review(**dict(args["review"], root=root, **({"reuse": False} if args["check"] == "knowledge_once" else {})))
            searches = web.calls + science.calls
            for _ in range(searches):
                meter.record()
            return facts(args["check"], args, root, record, searches, context, prior, ids)
    return run


def load_cases():
    return json.loads(Path(__file__).with_name("cases.json").read_text())


def score_case(fn, case):
    try:
        return judge(fn(case["kind"], case["args"]), case)
    except Exception as error:       # an arm that cannot produce the record fails the case
        return dict(ok=False, got=type(error).__name__, note=str(error)[:80])
