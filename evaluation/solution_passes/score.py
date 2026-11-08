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
    for kind in ("reaches", "verdict"):
        mine = [r for r in rows if r.get("kind") == kind]
        if mine:
            out[f"{kind}_passed"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    calls = [r["calls"] for r in rows if "calls" in r]
    if calls:
        out["calls_per_case"] = round(sum(calls) / len(calls), 2)
    return out
