# context_assembler_paraphrase

The harder question of the paper-collection stage: given a short description of a paper in other words, does the arm put that paper in
its first five results? Same 3,000-paper sample of our research-papers collection (identified by DOI in
`../context_assembler_papers/corpus_ids.json`), same stored `voyage-3.5-lite` vectors (no document is embedded), same arms, wiring and pass
rule as `../context_assembler_papers`. Only the query differs.

- **Cases** (`cases.json`, committed in full; the papers' titles and abstracts are public): the same 300 papers as the known-item stage,
  each with one paraphrase of the abstract's claim, 9 to 26 words, as a person who had not read the paper might type it. Each was written
  once by the cheapest Gemini text model (`gemini-2.5-flash-lite`, prompt in `score.py`), refused and rewritten up to 3 times if it shared
  a run of 4 consecutive words with the title or abstract (3 of 300 still did after 3 tries and were kept). Writing them took 108,497
  input and 6,008 output tokens, about $0.013 at that model's price ($0.10 and $0.40 per million tokens, `tier_prices.csv`), paid once and
  not part of an arm's row.
- **Pass**, details, queries and cost: as in the known-item stage (300 query embeddings, about $0.0002 for an arm that searches vectors).
- **Order of arms**: `bm25` first; a costlier arm is run only where the cheaper one leaves cases to win.
- **Run**: as in the known-item stage, `esoi run context_assembler_paraphrase --impl bm25` (and `vector`, `hybrid`, `composite`); rebuild
  the corpus from public sources with `../context_assembler_papers/rebuild_corpus.py`. `build_cases.py` regenerates the paraphrases
  (maintainers: it needs the collection and a Gemini key).
- **Limits**: one paraphraser, one pass; the paraphrase can still echo single distinctive words, which favours word matching.

## Results

<!-- results:start -->
| arm | pass (relevant in top 5) | 95% Wilson | nDCG@10 | recall@10 | median s/query | cost |
|---|---|---|---|---|---|---|
| bm25 | 257/300 (85.7%) | 81.2% to 89.2% | 0.8384 | 0.89 | 0.3 | $0.00 |
| bm25@analyzer=english | 270/300 (90.0%) | 86.1% to 92.9% | 0.8664 | 0.91 | 0.3 | $0.00 |
| vector | 295/300 (98.3%) | 96.2% to 99.3% | 0.9411 | 0.9967 | 0.1 | $0.00 |
| hybrid | 257/300 (85.7%) | 81.2% to 89.2% | 0.8384 | 0.89 | 0.3 | $0.00 |
| hybrid@vector_weight=1.0 | 284/300 (94.7%) | 91.5% to 96.7% | 0.8941 | 0.9867 | 0.3 | $0.00 |
| composite | 257/300 (85.7%) | 81.2% to 89.2% | 0.8384 | 0.89 | 0.4 | $0.00 |
<!-- results:end -->

Reading the table: `vector` finds 295 of 300 where `bm25` finds 257, and `bm25` with the English analyzer 270. The hub's `hybrid` and
`composite` equal `bm25` exactly: `hybrid` weights a vector hit at half a keyword hit when fusing ranks (a weight measured on another
task), which keeps every vector-only hit below all ten keyword hits, and `composite` lists the keyword hits first. With `vector_weight=1.0`
(plain reciprocal-rank fusion, the published method) `hybrid` reaches 284 of 300, still below `vector` alone on these queries: on
paraphrases the keyword list drags the fused order down.
