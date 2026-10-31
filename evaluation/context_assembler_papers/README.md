# context_assembler_papers

Do the arms find a known paper in a collection of scientific papers that is already embedded? The paper-collection stage of the
`context-assembler` seat, with queries that are a paper's **title** or a **sentence of its abstract**. The paraphrase stage
(`../context_assembler_paraphrase`) uses the same corpus with harder queries; the public benchmark stage is `../context_assembler`.

- **Corpus**: a 3,000-paper sample of our research-papers collection (5.0 million papers; abstracts of PubMed, bioRxiv, medRxiv and arXiv
  papers), identified by DOI (`corpus_ids.json`, in sample order: a DOI for 2,642 papers, else a PubMed or preprint id). The sample is the
  first 3,000 usable papers (title of 20 or more characters, abstract of 300 or more, a title not seen before) at or after a fixed point
  in the collection's id order, which is effectively random. We read it, read only, together with the vectors the collection stores;
  **no document is embedded for this stage**. The stored vectors come from Voyage `voyage-3.5-lite`.
- **Cases** (`cases.json`, committed in full; titles and abstracts are public): 300 papers, all different, drawn with a fixed seed: 150
  queries are the paper's title and 150 are one sentence of its abstract (60 to 400 characters, never containing the title). Each case
  has the query text and the paper's public identifier.
- **Pass**: the paper is among the first 5 ids the arm ranks (a mechanical known-item check). nDCG@10 and recall@10 are in the row's details,
  with `sample_sha`, a hash of the corpus identifiers.
- **Queries and cost**: only the 300 queries are embedded, once, with the collection's model (input type query); the vectors are cached.
  Each arm that searches vectors is charged those 7,765 tokens at $0.02 per million (Voyage pricing page, read 2026-10-31): about $0.0002.
- **Arms**: `bm25` over the title and abstract text (one file per paper), `vector` over the stored vectors (a local Qdrant folder rebuilt
  from them by an embedder that looks each text up; the hub's arms are unchanged), `hybrid` and `composite` combining the two; 10 hits,
  no model provider. Per the "skip a costlier arm that cannot beat a cheaper one already at 100%" rule, once `bm25` scores every case the
  others are not re-run on these cases.
- **Run**: needs the collection (`QDRANT_READONLY_URL` and `QDRANT_READONLY_API_KEY`, or `QDRANT_URL` and `QDRANT_API_KEY` for reads only,
  and `QDRANT_COLLECTION_RESEARCH_PAPERS`) and `VOYAGE_API_KEY`: `esoi run context_assembler_papers --impl bm25`. Without our collection,
  **reproduce it with your own embeddings**: `rebuild_corpus.py` fetches the same papers' titles and abstracts from PubMed and OpenAlex by
  the identifiers in `corpus_ids.json` (in a 60-paper test, 56 matched our stored titles; a few have no abstract at the public sources)
  and with `--embed` embeds them with `voyage-3.5-lite` (about 1.8 million tokens, about $0.04). Without `--embed` only `bm25` runs.
  `export_public_ids.py` and `build_cases.py` are the maintainers' scripts that wrote `corpus_ids.json` and `cases.json`.
- **Limits**: a known-item check on 3,000 papers is easy for an arm that matches words, so it is a sanity stage that shows an arm does
  not fail here, not which arm is cleverer. The stored vectors may have been made from text slightly different from title plus abstract.

## Results

<!-- results:start -->
| arm | pass (relevant in top 5) | 95% Wilson | nDCG@10 | recall@10 | median s/query | cost |
|---|---|---|---|---|---|---|
| bm25 | 300/300 (100.0%) | 98.7% to 100.0% | 1.0 | 1.0 | 0.3 | $0.00 |
| bm25@analyzer=english | 300/300 (100.0%) | 98.7% to 100.0% | 1.0 | 1.0 | 0.3 | $0.00 |
<!-- results:end -->

The vector (297 of 300) and hybrid (300 of 300) rows of the log were recorded on the same 300 papers before the cases carried their
query text, so they carry an earlier case hash and are not in the table; their numbers are in `esoi/results.csv`. `bm25` and `bm25` with
the English analyzer both pass all 300 on the final cases, so the costlier arms were not re-run.
