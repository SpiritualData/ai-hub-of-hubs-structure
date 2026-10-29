# Choosing the model for each tier

`ai_hub_of_hubs/tiers.py` picks, per tier, the (provider, model) arm that does the most passing work per unit of cost. The metric
decides; no provider or model is a default by preference.

- **Arms** are data in `registry/tier_arms.csv`: one default per tier and other providers as candidates, which are measured
  before they can replace a default.
- **Measurement** per arm: shared cases run, cases passed, tokens in and out.
- **Prices** are data in `registry/tier_prices.csv`: per million tokens, with `source_url` and `checked_on`. A row with a number
  needs both.
- **Credits** are data in `registry/tier_credits.csv`: a prepaid balance and an allowance per provider, and `credit_value`, what
  a credit is worth if it is not used here. Cost is the money spent after credits plus `credit_value` times the credits used, so
  credits lower the money spent and never count as free.
- **Rule**: highest passing cases per cost wins, the cheaper arm on a tie, and the reason is recorded. Nothing switches without a
  measurement of both the held arm and the winner.
- **Proof**: `tests/test_tiers.py` separates the rule from two broken baselines (always the most expensive model, always the
  cheapest whatever its quality).
