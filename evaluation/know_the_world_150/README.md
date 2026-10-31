# know_the_world_150

The next stage of `know_the_world`: 150 LitSearch questions instead of 40, to settle which arm the seat selects (Concept AI takes its study
source from that selection).

- **Cases** (`cases.json`, built by `build_cases.py`): the 40 cases of `know_the_world`, unchanged and first, plus 110 more drawn with
  seed 20261032 from the remaining LitSearch questions of quality 2 with exactly one gold paper. Same source, license, gold-title lookup
  and matching rule as `evaluation/know_the_world/README.md`; it is a new stage because the case file differs (a new `cases_sha`), so
  the 40-case rows stay as they are and are a subset.
- **Arms**: `web_research`, `openalex_semantic` (2 s between calls), and `openalex_semantic_and_web`, which interleaves the two arms' hit lists,
  drops duplicates by DOI or normalized title, keeps the first 5, and carries the web arm's summary text unchanged.
- **Cost**: Gemini tokens for the web arms at $0.10 in and $0.40 out per million (`gemini-2.5-flash-lite`, grounded prompts free up to
  1,500 a day); OpenAlex searches about $0.001 each against the daily allowance of a free key.
- Limits: the title match counts a web summary that mentions the title (`know_the_world/README.md`); 150 cases still leave intervals about
  8 points wide either side.

Run: `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run know_the_world_150 --impl openalex_semantic --sample 3`
