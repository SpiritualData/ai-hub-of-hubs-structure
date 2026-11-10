"""Scores a Structure Watch arm on scripted structures: does it raise the planted problem and route it right, stay silent on a clean structure, make no call on an unchanged digest, a run at its
ceiling or when off, raise a repeated item again only when it got worse, and keep to the caps (three items, 3000 tokens in, 500 out)? The model's reply is a fixed text in each case.
One number: the share of cases whose last step shows exactly what the case expects. No model call, no network."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

INPUT_CAP, OUTPUT_CAP = 3000, 500


def adapt(implementation, meter):
    from hubofhubs.the_body.internal_context.run_store.runs import RunStore
    from hubofhubs.the_consciousness.judgment_calls.judgment import SeverityPolicy
    from hubofhubs.the_intelligence.critical_thinking.esoi_application.apply import RecordFieldEdit

    def run(kind, args):
        store = RunStore("")
        records = copy.deepcopy(args["records"]) if args.get("records") else None
        applier = RecordFieldEdit(records=records).apply if records else None
        out = {}
        for number, step in enumerate(args["steps"]):
            replies = [step["model"]]
            arm = implementation(ask=lambda prompt, tier, cap: replies[0], store=store, judge=SeverityPolicy().decide, applier=applier, off=args.get("off", False), ceilings=args.get("ceilings"))
            structure = dict(copy.deepcopy(step["structure"]), review=args.get("review") or {}, now=f"2026-11-10T09:0{number}:00Z")
            out = arm.watch(structure, structure["now"])
        items = out.get("items") or []
        got = {"ran": out.get("reason") in ("first", "changed"), "subjects": sorted(i["subject"] for i in items), "routes": {i["subject"]: i["route"] for i in items},
               "caps": len(items) <= 3 and out.get("tokens_in", 0) <= INPUT_CAP and out.get("tokens_out", 0) <= OUTPUT_CAP}
        applied = next((i for i in items if i.get("route") == "applied"), None)
        if applied:
            got.update(before=applied["change"]["before"], after=applied["change"]["after"])
        if "records_unchanged" in kind_expect(args):
            got["records_unchanged"] = records == args["records"]
        return got

    def kind_expect(args):
        return args.get("expect_keys", ())
    return run


def score_case(fn, case):
    fn_args = dict(case["args"], expect_keys=[k for k in case["expect"]])
    return judge(fn(case["kind"], fn_args), case)
