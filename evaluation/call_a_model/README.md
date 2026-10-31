# call_a_model

Quality per dollar of each vendor arm at its cheapest current model, on exact-answer maths word problems. Paid: run it staged.

- **Dataset**: GSM8K test split, official file `grade_school_math/data/test.jsonl` of https://github.com/openai/grade-school-math
  (1,319 problems), repository commit `3101c7d5072418e28b9008a6636bde82a006892c` (2021-11-19, the latest commit on 2026-10-31),
  file sha256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`. License: MIT (Copyright 2021 OpenAI, the repository's
  `LICENSE`). Cobbe et al., "Training Verifiers to Solve Math Word Problems", 2021.
- **Sample**: 50 cases, `random.Random(20261031).sample(range(1319), 50)` over the file's line numbers, sorted; ids `gsm8k-test-<line>`.
  Rebuild with `python3 scripts/sample_gsm8k.py test.jsonl --n 50 --seed 20261031`. Only the sample is committed (`cases.json`).
- **Pass**: the number after the last `Final answer:` line equals the gold answer after `####` exactly.
- **Models** (cheapest text model on each vendor's pricing page, 2026-10-31; prices in `hubofhubs/registry/tier_prices.csv`):
  `gemini-2.5-flash-lite` ($0.10 in, $0.40 out per million tokens), `gpt-5-nano` ($0.05, $0.40; a reasoning model, default effort),
  `deepseek-flash` ($0.30, $1.20, the peak-hours rate, so cost is never understated; thinking off, the arm's default). Cost is the
  metered tokens (thinking tokens included) times that price.
- **Anthropic**: not measured. Its API account is capped until 2026-11-01, so no call was made (`--impl anthropic` refuses).
  No public evidence row is entered for it yet (the evidence registry has no model area).
- **Not ranked**: see `invariant.txt`. The vendors are evidence for per-tier choice, not rivals for the seat.
- **Free check**: `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run call_a_model --impl no_answer` (a baseline, no model).
- **Staged paid run** (per vendor, stop a vendor that errors): `esoi run call_a_model --impl gemini --sample 3 --record`, then `--sample 10`,
  then no `--sample`.
- Limits: 50 problems give wide intervals; one prompt; one run per cell.
