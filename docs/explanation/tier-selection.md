# Choosing the model for each tier

**Public evaluations decide the model of a tier.** Each of the four tiers (fast, balanced, quality, best) has its own metric over public
evaluations, list prices and published speed. `model_tier_chooser/tier_metrics.csv` holds each tier's anchor (its held default), the tolerance,
the cost and speed weights and the small capability bonus, each with its reason, and `registry/tier_public_scores.csv` holds one row per model and
reasoning effort with the numbers, their source URL and the date checked. The minimum of a tier is what does the tier's job today: for each evaluation the tier names, the score of the tier's held default
(`tier_arms.csv`, the anchor, recorded with its model and date in `tier_metrics.csv`) at its documented default effort, less a 5 percent
tolerance for benchmark noise. An evaluation on which the anchor has no current number is dropped and listed, never guessed. An arm with a current
number on the rest, a list price and a published output speed is eligible; it clears the tier when it reaches every minimum, so the held default
always clears its own. Among the arms that clear, the cheapest and fastest wins:
`score = K^wc x S^ws x (1 + bonus x C)`, where `K` is the cheapest clearing arm's list price (input plus output per million tokens) divided by the
arm's, `S` is the arm's speed divided by the fastest clearing arm's, `wc + ws = 1` and `C` is the share of the best value on the tier's evaluations.
The bonus is at most 10 percent for fast, 30 for balanced and 60 for quality, so capability above the minimum never outweighs a large price
difference, and a tier never moves to a dearer model merely because a stronger one exists. A tier moves up only by a recorded change to its anchor
with the solution-level evidence that its work needs more. Best has no minimum and uses capability alone. A missing number means not eligible (nothing is imputed), rows older than 45 days are not
used (the held default of `tier_arms.csv` then stays), and an arm at an effort other than the model's documented default competes only when its caller
applies the effort. A tier whose evaluations only stand in for its use is marked proxy evidence in its result. `choose` returns the arm, its effort,
the reason with the runner-up, the evidence mark and the score breakdown. `science` is a call role, not a tier: `choose(role="science")` applies the
role's capability weights inside the fast tier (its minimums are the held default's scores on those evaluations) and `science` reads as an alias of fast.

**Where own measurement goes.** The hub's own measurements do not decide which model a tier maps to; they are small, and public evaluations decide
that. A solution's own metric informs which tier its call role uses (the `evidence` column of `role_tiers.csv`). The functions `select` and `pick`
below stay available over measured arms.

**Direction.** The single ladder is meant to become tiers per type of task, each with its own public metric. The science role variant is the first
example: a role that replaces a tier's capability weights while keeping its cost and speed factors.

The rest of this page describes the passing-work-per-cost functions.

`hubofhubs/the_world/model_plumbing/model_tier_chooser/tiers.py` picks, per tier, the (provider, model) arm that does the most passing work per unit of cost. The metric
decides; no provider or model is a default by preference.

- **Arms** are data in `registry/tier_arms.csv`: one default per tier and other providers as candidates, which are measured
  before they can replace a default.
- **Measurement** per arm: shared cases run, cases passed, tokens in and out.
- **Prices** are data in `registry/tier_prices.csv`: per million tokens, with `source_url` and `checked_on`. A row with a number
  needs both.
- **Price rows** may have several rows for one model: `from_prompt_tokens` is a higher rate for prompts at least that long (Claude
  Haiku 5.5 above 100,000 tokens), and `valid_from` / `valid_until` a price change on a date (Gemini 3.6 Flash on 2027-01-01).
  Arm cost uses the base row; `tiers.list_cost` takes the prompt length.
- **Credits** belong to the consumer: a prepaid balance and an allowance per provider, and `credit_value`, what a credit is worth
  if it is not used here. The consumer passes its rows to `tiers.choose(credits=...)` (or `pick`) with the columns of
  `registry/tier_credits.csv`: `provider`, `balance`, `allowance`, `credit_value`. That file ships with the header only, because
  an organization's allowance is private to it. Cost is the money spent after credits plus `credit_value` times the credits
  used, so credits lower the money spent and never count as free. A blank `credit_value` is counted at face value (1), the
  reading that never understates cost; the value is set only by the owner of the credit. Example row (not data):
  `anthropic,,100,0.5,USD,monthly`.
- **Measurements** are data in `registry/tier_measurements.csv` (tier, provider, model, cases, passed, tokens, source,
  measured_on), written only from a metric run. None exists yet, so `tiers.choose` keeps each tier's default arm.
- **`tiers.choose(available=...)`** reads all four files and returns the arm per tier, with the reason. A consumer passes the
  providers it has configured: an arm of another provider is not offered, and a tier whose held default is not available gets the
  cheapest priced available arm, with that reason, because nothing else can run.
- **Rule**: highest passing cases per cost wins, the cheaper arm on a tie, and the reason is recorded. Nothing switches without a
  measurement of both the held arm and the winner.
- **Proof**: `hubofhubs/the_world/tests/test_tiers.py` separates the rule from two broken baselines (always the most expensive model, always the
  cheapest whatever its quality).
