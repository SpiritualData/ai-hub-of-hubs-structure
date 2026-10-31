# model_quality_aime

How well many current models do hard exact-answer maths, measured the same way, and fed to the tier selector
(`hubofhubs/registry/tier_measurements.csv`, see `docs/explanation/tier-selection.md`). Paid: run it staged, cheapest first.

- **Benchmark**: AIME 2025 I and II, 30 problems, each with an integer answer from 0 to 999. The problems are published by the
  Mathematical Association of America (MAA). A mirror's license does not settle the MAA's rights in the text, so **the text is not committed**:
  `cases.json` holds the 30 ids, the gold answers, the mirror line of each problem and the sha256 of each problem text, and `problems.py` downloads
  and checks the text.
- **Source**: Hugging Face dataset `opencompass/AIME2025` (MIT on its dataset card), commit `a6ad95f611d72cf628a80b58bd0432ef6638f958`
  (2025-02-25): `aime2025-I.jsonl` sha256 `b91b3c96f05d9635d2a0692b124ebe023c1ff59cb19c074275e6c4b349d0659e`, `aime2025-II.jsonl` sha256
  `16a2dcfbbf9db1b11f8a69a3ba5e4cac73e3641b19a37e2307e9c12240bbed5e`. The mirror's gold for one problem (II-05) reads `336^\circ`; our gold is the integer.
  All 30 gold answers equal the `MathArena/aime_2025` dataset's (CC BY-NC-SA 4.0), checked 2026-10-31. Problem text is fetched to `data/` (git-ignored).
- **One prompt for every model** (`runners.py`), the problem text appended after a blank line:

      Solve this problem. Think it through, then end with one last line of exactly this form, with only the integer (from 0 to 999, no units, no commas): Final answer: <integer>

- **Pass** = the integer after the last `Final answer:` equals the gold answer exactly. If a model gave no such line, the last `\boxed{<integer>}` counts
  (a model that boxes its answer instead of using the asked line is not failed for format). Nothing else is accepted: no number, a non-integer or a
  truncated answer fails.
- **Reasoning is on for every model that has it, and is a recorded circumstance** (one call per problem, one run per cell). The API arms are
  capped at **32,768 output tokens per call**, so a very long reasoning run ends with no answer and fails; the three Claude arms (`claude -p`) have
  no explicit cap:

  | Arm | Model | Reasoning setting |
  |---|---|---|
  | gemini_2_5_flash_lite, gemini_2_5_flash | the same names | `thinking_budget=-1` (dynamic thinking on) |
  | gpt_5_nano, gpt_5_mini | the same names | `reasoning_effort=medium` |
  | deepseek_flash, deepseek_v4_pro | the same names | thinking enabled |
  | claude_haiku, claude_sonnet, claude_opus | the CLI's latest haiku, sonnet and opus | `claude -p --effort high`, no tools |

- **Cost**: API arms are the metered tokens (thinking included) times `tier_prices.csv`; DeepSeek is priced at the peak rate. Claude runs through
  `claude -p` on the existing subscription with the API key variables removed from the child process: cost is recorded as **subscription**
  (calls counted, no dollars). Its token counts are what the CLI reports and include its fixed system prompt (about 3,000 tokens a call), so they
  overstate what a bare API call would use; the tier measurement says so.
- **Spend rule**: the API arms together stay under USD 2.50. Each stage was estimated from the stage before it and `tier_prices.csv`.
- **Stages** (a model that errors is stopped): `esoi run model_quality_aime --impl <arm> --sample 3 --record`, then without `--sample`.
- **Free check**: `esoi run model_quality_aime --impl no_answer` (a baseline, no model; 0 of 30).
- **Contamination**: the AIME 2025 problems and answers were public from February 2025, so a model trained after that may have seen them. MathArena
  flags the same risk. Read every pass rate here as an upper bound for models released after early 2025, and treat the small gaps between neighbours
  as noise.
- **Claude arms, checked**: each run used `claude -p ... --tools "" --setting-sources "" --strict-mcp-config`. A stream-json probe with the same flags
  shows `tools: []`, no MCP servers, one turn, no tool-use event (the model asked for Bash and was refused), and the CLI reports the model id actually
  used (`claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, recorded in the results). The three Claude arms are therefore pure text like the API
  arms, and were not re-run. Haiku 30/30 against Opus 29/30 is inside the interval width, not a ranking.
- **Failures with no parsable answer** (neither a `Final answer:` integer nor a `\boxed{}` integer) against wrong integers, of the 30 problems:
  claude_haiku 0 / 0, claude_opus 1 / 0, claude_sonnet 2 / 1, deepseek_flash 1 / 1, gemini_2_5_flash 6 / 4, gemini_2_5_flash_lite 11 / 2,
  gpt_5_mini 0 / 3, gpt_5_nano 1 / 9. The Gemini no-answer cases are probably runs that spent the whole cap on thinking (not checked), so those two
  arms are lower bounds on what the models can do with a larger cap.
- Limits: 30 problems give wide intervals, so neighbours are not ranked; the problems have been public since early 2025, so training contamination is
  possible (the independent MathArena rows carry the same caveat); one run per cell.
