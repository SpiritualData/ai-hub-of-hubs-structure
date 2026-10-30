# Choosing the model for each tier

`hubofhubs/tiers.py` picks, per tier, the (provider, model) arm that does the most passing work per unit of cost. The metric
decides; no provider or model is a default by preference.

- **Arms** are data in `registry/tier_arms.csv`: one default per tier and other providers as candidates, which are measured
  before they can replace a default.
- **Measurement** per arm: shared cases run, cases passed, tokens in and out.
- **Prices** are data in `registry/tier_prices.csv`: per million tokens, with `source_url` and `checked_on`. A row with a number
  needs both.
- **Price rows** may have several rows for one model: `from_prompt_tokens` is a higher rate for prompts at least that long (Claude
  Haiku 5.5 above 100,000 tokens), and `valid_from` / `valid_until` a price change on a date (Gemini 3.6 Flash on 2027-01-01).
  Arm cost uses the base row; `tiers.list_cost` takes the prompt length.
- **Credits** are data in `registry/tier_credits.csv`: a prepaid balance and an allowance per provider, and `credit_value`, what
  a credit is worth if it is not used here. Cost is the money spent after credits plus `credit_value` times the credits used, so
  credits lower the money spent and never count as free. The Anthropic row holds the 200 USD monthly allowance (Joshua's
  direction of 2026-10-30; the `source_url` is the billing page where it is confirmed) and leaves `credit_value` blank:
  unconfirmed, for Payal to confirm. A blank value is counted at face value (1), the reading that never understates cost.
- **Measurements** are data in `registry/tier_measurements.csv` (tier, provider, model, cases, passed, tokens, source,
  measured_on), written only from a metric run. None exists yet, so `tiers.choose` keeps each tier's default arm.
- **`tiers.choose(available=...)`** reads all four files and returns the arm per tier, with the reason. A consumer passes the
  providers it has configured: an arm of another provider is not offered, and a tier whose held default is not available gets the
  cheapest priced available arm, with that reason, because nothing else can run.
- **Rule**: highest passing cases per cost wins, the cheaper arm on a tie, and the reason is recorded. Nothing switches without a
  measurement of both the held arm and the winner.
- **Proof**: `tests/test_tiers.py` separates the rule from two broken baselines (always the most expensive model, always the
  cheapest whatever its quality).
