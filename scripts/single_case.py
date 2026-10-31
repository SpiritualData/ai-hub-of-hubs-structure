"""One real case for the top-level solution: assemble the hub in one line, then answer one trivial question through the
seats that can run. Run: python3 scripts/single_case.py --model-call-factory package.module:function [--provider NAME]

The consumer provides the ``model-call`` seat. ``--model-call-factory`` names a function in the consumer's code that returns an
object with ``complete(prompt, tier)`` (and, optionally, ``usage()`` returning ``tokens_in`` and ``tokens_out``); the hub never
imports a consumer except here, at the operator's request. The case passes when the reply contains the expected digit, the
assembly names a reason for the model-call and reason-and-answer seats, and the cost is reported (list price when the arm is priced).
"""
import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hubofhubs  # noqa: E402
from hubofhubs import registry, tiers  # noqa: E402

QUESTION = "What is 2+2? Answer with the digit."
EXPECTED = "4"
TIER = "cheap"


def run(model_call, provider="anthropic", question=QUESTION, expected=EXPECTED, tier=TIER):
    """Assemble with the consumer's model-call, choose the tier's arm, ask once, and return the case record."""
    system = hubofhubs.assemble(provided={"model-call": model_call})
    chosen = tiers.choose(available={provider})[tier]
    reply = system["model-call"].complete(question, tier=tier)
    usage = model_call.usage() if hasattr(model_call, "usage") else {}
    arm = chosen["arm"]
    tokens_in, tokens_out = int(usage.get("tokens_in", 0)), int(usage.get("tokens_out", 0))
    cost = tiers.list_cost(registry.read("tier_prices.csv"), arm[0], arm[1], tokens_in, tokens_out) if arm else None
    reasons = [r for r in system.reasons if r.startswith(("model-call", "reason-and-answer"))]
    return {"question": question, "reply": reply, "tier": tier, "arm": list(arm) if arm else None, "arm_reason": chosen["reason"],
            "reasons": reasons, "tokens_in": tokens_in, "tokens_out": tokens_out,
            "list_cost_usd": cost, "reported_cost_usd": usage.get("cost_usd"),
            "contains_expected": expected in reply, "has_both_reasons": len(reasons) == 2, "cost_reported": cost is not None or "cost_usd" in usage,
            "pending": sorted(system.pending)}


def passed(record):
    return bool(record["contains_expected"] and record["has_both_reasons"] and record["cost_reported"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-call-factory", required=True, help="package.module:function returning the consumer's model-call")
    parser.add_argument("--provider", default="anthropic", help="the provider whose arm the tier selector may choose")
    args = parser.parse_args(argv)
    module, _, name = args.model_call_factory.partition(":")
    record = run(getattr(importlib.import_module(module), name)(), provider=args.provider)
    print(json.dumps(record, indent=2, default=str))
    return 0 if passed(record) else 1


if __name__ == "__main__":
    raise SystemExit(main())
