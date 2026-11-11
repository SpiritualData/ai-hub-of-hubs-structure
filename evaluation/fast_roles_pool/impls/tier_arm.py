"""A tier's model on the pooled cases. One arm, parameters name which: ``--impl tier_arm@tier=fast`` (the tier's held default), ``@tier=balanced``
(the reference), ``@tier=fast,candidate=2`` (the second candidate the tier's table lists, by order of ``tier_arms.csv``).

The model comes from the tier table (``tier_arms.csv`` through ``tiers.default_arms``), never from this file. Anthropic models run on the operator's Claude
CLI login (no key, no tools; cost is what the CLI reports, informational on a subscription); any other provider uses its key from the environment and the
hub's provider class. A provider with no key stops the arm with a clear message and is recorded as a gap, not as a failure."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from priced import first_env, price_of, priced  # noqa: E402

PAID = True
MAX_OUTPUT = 4000
KEYS = {"openai": ("OPENAI_API_KEY",), "deepseek": ("DEEPSEEK_API_KEY",), "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY")}


def arm_of(tier, candidate):
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import tiers
    held, candidates = tiers.default_arms()
    if not candidate:
        return held[tier]
    return candidates[tier][candidate - 1]


def build(meter, tier="fast", candidate=0):
    provider_name, model = arm_of(tier, candidate)
    meter.model = model
    if provider_name == "anthropic":
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
        engine = meter.wrap(ClaudeCliProvider(claude_path="claude"), ("answer",))

        def ask(kind, args):
            return engine.answer([{"role": "user", "content": args["prompt"]}], model=model, system=args.get("system"))
        return ask
    key = first_env(*KEYS.get(provider_name, ()))
    if not key:
        raise RuntimeError(f"no key for {provider_name} in the environment: {model} cannot be run here")
    if provider_name not in ("openai", "deepseek"):
        raise RuntimeError(f"{provider_name} is not wired in this stage")
    import hubofhubs.the_world.model_plumbing.vendor_model_caller.openai as vendor
    engine = priced(vendor.OpenAIProvider if provider_name == "openai" else vendor.DeepSeekProvider, price_of(provider_name, model))(api_key=key)
    meter.wrap(engine, ("complete",))
    limit = "max_completion_tokens" if provider_name == "openai" else "max_tokens"

    def ask(kind, args):
        messages = ([{"role": "system", "content": args["system"]}] if args.get("system") else []) + [{"role": "user", "content": args["prompt"]}]
        return engine.complete(model, messages, **{limit: MAX_OUTPUT}).choices[0].message.content or ""
    return ask
