"""Shared by the components that call a real model: provider arms that count their tokens (thinking tokens included) and turn them
into dollars with a price from ``hubofhubs/registry/tier_prices.csv``. A model with no price row costs ``None``, never zero."""
import csv
import os
from pathlib import Path

PRICES = Path(__file__).resolve().parent.parent / "hubofhubs" / "registry" / "tier_prices.csv"


def price_of(provider, model):
    """``(input, output)`` dollars per million tokens for the base row of ``model`` (no long-prompt tier, no date window), or None."""
    with PRICES.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["provider"] == provider and row["model"] == model and not row["from_prompt_tokens"] and not row["valid_from"]:
                return float(row["input_per_mtok"]), float(row["output_per_mtok"])
    return None


def first_env(*names):
    """The value of the first of these environment variables that is set (evaluation code may read the environment; the hub package may not)."""
    return next((os.environ[n] for n in names if os.environ.get(n)), None)


def priced(base, price):
    """``base`` (a provider class) as a subclass that exposes ``cost_usd`` from its token counters and ``price`` (None: unknown)."""
    class Priced(base):
        @property
        def cost_usd(self):
            return 0.0 if price is None else (self.tokens_in * price[0] + self.tokens_out * price[1]) / 1_000_000
    return Priced
