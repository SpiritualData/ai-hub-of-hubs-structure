"""Scores a vendor arm of the call-a-model seat on grade-school maths word problems: quality per dollar at the vendor's cheapest current model.

Cases are a fixed-seed sample of the GSM8K test split (see README.md). The model is asked for the answer on a last line
``Final answer: <number>``; pass = that number equals the gold answer exactly. Tokens, thinking tokens included, are metered from the
provider and priced from ``hubofhubs/registry/tier_prices.csv``. Anthropic is not run: its API account is capped until 2026-11-01.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from priced import first_env, price_of, priced  # noqa: E402

PROMPT = ("Solve this problem. Think it through briefly, then end with one last line of exactly this form, with only the number "
          "(no units, no commas): Final answer: <number>\n\n{question}")

# arm class -> (price provider, cheapest current model on the vendor's pricing page on 2026-10-31, environment variables for the key)
VENDORS = {
    "GeminiProvider": ("gemini", "gemini-2.5-flash-lite", ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY")),
    "OpenAIProvider": ("openai", "gpt-5-nano", ("OPENAI_API_KEY",)),
    "DeepSeekProvider": ("deepseek", "deepseek-flash", ("DEEPSEEK_API_KEY",)),
}


CLAUDE_MODEL = "claude-haiku"   # the cheapest Claude family; the CLI maps it to the latest Haiku


def final_number(text):
    """The number after the last ``Final answer:`` as a float, or None."""
    found = re.findall(r"final answer:\s*\$?\s*(-?[\d,]*\.?\d+)", text or "", flags=re.IGNORECASE)
    return float(found[-1].replace(",", "")) if found else None


def adapt(implementation, meter):
    from esoi.harness import RunError
    name = implementation.__name__
    if name == "ClaudeCliProvider":
        # Runs on the Claude Code subscription: no key, no per-token price. Tokens are those the CLI reports; cost is the CLI's own list-price figure.
        provider = implementation(claude_path="claude", timeout_seconds=300, environment=dict(os.environ))
        meter.model = CLAUDE_MODEL
        meter.wrap(provider, ("answer",))

        def run_cli(kind, args):
            return provider.answer([{"role": "user", "content": PROMPT.format(question=args["question"])}], model=CLAUDE_MODEL)
        return run_cli
    if name not in VENDORS:
        raise RunError(f"{name} is not run here: the Anthropic API account is capped until 2026-11-01, so it is recorded as not measured")
    vendor, model, variables = VENDORS[name]
    provider = priced(implementation, price_of(vendor, model))(api_key=first_env(*variables))
    meter.model = model
    meter.wrap(provider, ("answer",))

    def run(kind, args):
        return provider.answer([{"role": "user", "content": PROMPT.format(question=args["question"])}], model=model)
    return run


def score_case(fn, case):
    text = fn(case["kind"], {"question": case["question"]})
    got, want = final_number(text), float(case["expect"])
    ok = got is not None and got == want
    return dict(ok=ok, got="none" if got is None else f"{got:g}", note="" if ok else f"expected {case['expect']}")
