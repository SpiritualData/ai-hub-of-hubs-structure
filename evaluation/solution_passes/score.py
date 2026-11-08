"""Scores a Solution Passes arm on requests whose right answer depends on a record the hub's own network holds (each case names a change
that a measured result in that solution's records already argues against).

``reaches`` (free, no model): the solution the record belongs to is named by Relevant Solutions and the deciding record is in the prompt
its records form. ``verdict`` (a real cheap pass): that solution's own pass reports a conflict or risk that cites the measured result.
The knowledge mode (``retrieved``, ``all``, ``none``) is the case argument ``knowledge`` or the arm parameter. The model-calling stage asks the
``cheap`` tier through Model Plumbing (the tier chooser picks the model; this file names none) and runs only with ``--max-calls``."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
ROOT = Path(__file__).resolve().parents[2]


class Plumbing:
    """Model Plumbing for this component: one question at the cheap tier, counted by the meter."""

    def __init__(self, meter):
        import hubofhubs.api as hub
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
        self.hub, self.options, self.meter = hub, {"vendor-model-caller": {"primary": ClaudeCliProvider()}}, meter

    def ask(self, prompt, tier=""):
        return self.hub.run("model-plumbing", {"prompt": prompt, "tier": tier or "cheap"}, options=self.options)


def prepared(request, knowledge):
    from hubofhubs.api import RecordsIndex, briefs, network_of
    found = RecordsIndex().relevant(request, str(ROOT))["solutions"]
    return briefs(network_of(str(ROOT)), found, request, knowledge)


def adapt(implementation, meter, knowledge="retrieved"):
    def run(kind, args):
        if kind == "depth":
            return depth_case(meter, args)
        made = prepared(args["request"], args.get("knowledge") or knowledge)
        if kind == "reaches":
            return {"briefs": made}
        arm = implementation(plumbing=Plumbing(meter))
        return {"briefs": made, "considered": dict(arm.consider(args["request"], made))}
    return run


def finding_text(finding):
    parts = [str(finding.get("needs") or "")] + [str(r) for r in finding.get("risks") or []]
    parts += [" ".join(str(v) for v in (c.values() if isinstance(c, dict) else [c])) for c in finding.get("conflicts") or []]
    return " ".join(parts).lower()


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    if case["kind"] == "depth":
        return {"id": case["id"], "kind": "depth", "one_call": got.get("before"), "depth": got.get("after"), "calls": got.get("calls"),
                "ok": (got.get("after") or 0) > (got.get("before") or 0) or got.get("before") == 1, "met": got.get("met")}
    sid = case["expect"]["solution"]
    brief = next((b for b in got["briefs"]["solutions"] if b["solution_id"] == sid), None)
    row = {"id": case["id"], "kind": case["kind"], "named": brief is not None, "prompt_chars": len((brief or {}).get("prompt", ""))}
    if case["kind"] == "reaches":
        row["ok"] = brief is not None and case["expect"]["record"] in brief["prompt"]
        return row
    considered = got.get("considered") or {}
    finding = next((f for f in considered.get("findings") or [] if f["solution_id"] == sid), None)
    text = finding_text(finding or {})
    row.update(calls=considered.get("calls", 0), conflicts=len((finding or {}).get("conflicts") or []),
               ok=finding is not None and bool((finding or {}).get("conflicts")) and any(c.lower() in text for c in case["expect"]["cites"]))
    return row


def aggregate(rows):
    out = {}
    deep = [r for r in rows if r.get("kind") == "depth"]
    if deep:
        out["one_call_mean"] = round(sum(r["one_call"] or 0 for r in deep) / len(deep), 3)
        out["depth_mean"] = round(sum(r["depth"] or 0 for r in deep) / len(deep), 3)
        out["depth_calls_per_case"] = round(sum(r["calls"] or 0 for r in deep) / len(deep), 2)
    for kind in ("reaches", "verdict"):
        mine = [r for r in rows if r.get("kind") == kind]
        if mine:
            out[f"{kind}_passed"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    calls = [r["calls"] for r in rows if "calls" in r]
    if calls:
        out["calls_per_case"] = round(sum(calls) / len(calls), 2)
    return out


WRITE = "Write the following. Use no em dashes. Reply with the text only.\n\n{prompt}\n\nWhat to write: {goal}\nIt must meet every one of these:\n{requirements}"
JUDGE = ("For each numbered requirement, say whether the text meets it, and quote the exact words of the text that show it. Reply with JSON only: "
         "{{\"items\": [{{\"n\": 1, \"met\": true, \"quote\": \"<exact words from the text>\"}}]}}\n\nRequirements:\n{requirements}\n\nText:\n{text}")


def parse_reply(text):
    import json
    raw = str(text or "")
    start, end = raw.find("{"), raw.rfind("}")
    try:
        found = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def rubric_check(ask):
    """The rubric's own check, never the writer: a requirement counts as met only when the judge says so and its quote is found in the text."""
    def check(text, item):
        reqs = list(item["requirements"])
        listing = "\n".join(f"{n}. {r}" for n, r in enumerate(reqs, 1))
        got = parse_reply(ask(JUDGE.format(requirements=listing, text=text)))
        met = set()
        for row in got.get("items") or []:
            quote = " ".join(str(row.get("quote") or "").split())
            if row.get("met") is True and quote and quote.lower() in " ".join(text.split()).lower() and isinstance(row.get("n"), int) and 1 <= row["n"] <= len(reqs):
                met.add(row["n"] - 1)
        missing = [r for n, r in enumerate(reqs) if n not in met]
        return {"met": not missing, "score": round(len(met) / len(reqs), 3), "missing": missing}
    return check


def writer(ask):
    def work(item):
        return ask(WRITE.format(prompt=item.get("prompt", ""), goal=item["goal"], requirements="\n".join(f"- {r}" for r in item["requirements"])))
    return work


def depth_case(meter, args):
    """The one-call deliverable and the same deliverable given depth (build_out), scored by the same rubric check."""
    from hubofhubs.api import build_out
    plumbing = Plumbing(meter)
    ask = lambda prompt: plumbing.ask(prompt, "cheap")
    item = {"goal": args["goal"], "requirements": args["requirements"], "prompt": ""}
    work, check = writer(ask), rubric_check(ask)
    one = work(item)
    from hubofhubs.api import verbatim_combine
    return dict(build_out(item, work, check, combine=verbatim_combine(ask), base=one))
