# context_assembler_papers

The private stage of the `context-assembler` seat: do the arms find a known paper in an existing, already embedded collection of
scientific papers? The public stage is `evaluation/context_assembler` (NFCorpus). This repository holds the method and the numbers
only; no paper text, title or id is committed or published.

- **Corpus**: a fixed sample of 3,000 papers read, read only, from the 5.0 million point production Qdrant collection of paper
  abstracts, with the vectors that collection already stores. Nothing is written to it and **no document is embedded**. The sample
  is the first 3,000 usable points (title of 20 or more characters, abstract of 300 or more, a title not seen before) at or after a
  fixed point id, in point-id order (ids are content hashes, so the order is effectively random). Each run records `sample_sha`, a hash
  of the sampled ids, so two runs can be shown to have seen the same corpus without publishing any id.
- **Cases** (`cases.json`: a position in the sample and a kind, nothing else): 300 queries, all about different papers, drawn with a fixed
  seed. 150 are the paper's **title**; 150 are one **sentence of its abstract** (60 to 400 characters, picked with a fixed seed, never
  containing the title).
- **Pass**: the paper the query was made from is among the first 5 ids the arm ranks (a mechanical known-item check). nDCG@10 and
  recall@10 are in the row's details.
- **Embedding**: only the 300 queries are embedded, once, with the model that embedded the collection (Voyage `voyage-3.5-lite`,
  input type query, found in the backend's embedding service and its research-chat query path), and the vectors are cached. Each arm that
  searches vectors is charged those queries' 7,765 tokens at $0.02 per million (Voyage pricing page, read 2026-10-31): about $0.0002.
  The local store the vector arm searches is rebuilt from the pulled vectors by handing the store an embedder that looks each text up in
  them; the hub's arms are unchanged.
- **Arms**: `bm25` over the pulled text (one file per paper), `vector` over the pulled vectors, `hybrid` and `composite` combining the two,
  all with 10 hits and no model provider. Rank is read as in the public stage.
- **Run**: `esoi run context_assembler_papers --impl bm25` (and `vector`, `hybrid`, `composite`) with `QDRANT_READONLY_URL`,
  `QDRANT_READONLY_API_KEY` (or `QDRANT_URL`, `QDRANT_API_KEY`, read only), `QDRANT_COLLECTION_RESEARCH_PAPERS` and `VOYAGE_API_KEY` in the
  environment; without them the stage is not measured. The cache holds paper text in a private temporary folder; delete it after a run.
- **Limits**: a known-item check on 3,000 papers is easy, so an arm that finds almost everything leaves little to separate; the stage
  shows whether an arm fails at all on this kind of corpus, not which is cleverer. The stored vectors may have been made from a
  different text than title plus abstract. Titles and abstract sentences are not paraphrased, which favours lexical search.
