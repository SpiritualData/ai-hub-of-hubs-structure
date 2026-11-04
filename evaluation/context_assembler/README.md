# context_assembler

Does the arm put a document that answers the query in its first five results? Four arms of the `context-assembler` seat
(`bm25`, `vector`, `hybrid`, `composite`), the memory-and-recall sub-seat of the hub, compared on the same queries.

One component, one number: accuracy, cost and time are folded by `[balance.context_assembler]` in `esoi.toml`, and the case set pools three
sources (`mix.py`, files of `datasets/`, each with the module that knows its corpus): `nfcorpus` (`nfcorpus.py`, the public benchmark
below), `papers` (`papers.py`, title and abstract-sentence queries over a paper sample) and `paraphrase` (`paraphrase.py`, paraphrased
queries over the same sample). A source is a case source, never a stage or a leaderboard of its own; the row's details give each source's
raw result (`nfcorpus_passed`, `papers_passed`, `paraphrase_passed`). The papers sources read a private collection, so a run without its
settings stops with "not measured" and never scores the public part alone under this name.

### Source: nfcorpus (public benchmark)

- **Cases** (`datasets/nfcorpus.json`): the 323 test queries of the public BEIR **NFCorpus** benchmark (medical questions from a nutrition
  site, judged against 3,633 PubMed abstracts, relevance grades 1 and 2). That is the whole official test split, not a sample, so
  the figures can be set beside the BEIR paper. The file holds ids and grades only.
- **Corpus**: the whole NFCorpus corpus (3,633 documents, every gold document plus all the benchmark's distractors); nothing is
  sub-sampled. The arms see the same text: title, blank line, abstract.
- **License, stated honestly.** The BEIR code is Apache-2.0; the Hugging Face card for the BEIR copy says CC BY-SA 4.0; the BEIR
  paper (appendix E) says NFCorpus reports no license in the paper or repository; the NFCorpus authors say "free to use for
  academic purposes" and point to the NutritionFacts.org terms for any other use. Because redistribution is not allowed by any of
  these, **this repository commits only ids and grades**. `nfcorpus.py` downloads the zip from the official BEIR URL on first use,
  refuses it unless its sha256 is `efe5be03...71b0b` (full value in `nfcorpus.py`), and caches it in the system temporary folder.
- **Pass**: at least one relevant document in the first 5 ids the arm ranks. `aggregate` also prints nDCG@10 (gain = grade,
  discount log2(rank + 1), as BEIR's `ndcg_cut_10`) and recall@10; `aggregate` returns them and `esoi run --record` writes them into the row's `details`. `results_table.py` builds the table below from the records.
- **Measured arms: `bm25` and `vector`. `hybrid` and `composite` are not measured: embedding budget not authorized.** Their wiring
  below is what a run would use; the vector index they would share was not extended or re-built for them.
- **Arms and wiring** (all four are wired in `nfcorpus.py`; all with 10 hits, no model provider: no query rewriting, no review, no consolidation, so no model call
  and $0): `bm25` is the BM25 content store over one `.txt` file per document; `vector` is the vector assembler over a local
  Qdrant folder embedded with `BAAI/bge-small-en-v1.5` (fastembed, 4 ONNX threads, the hub's default model); `hybrid` fuses
  those two by reciprocal rank; `composite` runs both and concatenates their lists (bm25 first). Rank is read from `card_ids`,
  except for `vector`, whose `card_ids` are sorted by id by design, so its `effective_score` order is used.
- **Free stage**: `PYTHONPATH=.:../evolvable-structure/implementations/python OMP_NUM_THREADS=4 python3 -m esoi run context_assembler --impl bm25`
  ; add `--record` to log it. `vector`, `hybrid` and `composite` embed the 3,633 documents once (about 14 minutes on 4 threads for the recorded run) and need a person's authorization first. Rebuild `datasets/nfcorpus.json` with `build_nfcorpus_cases.py`.
- **Limits**: one domain (biomedical abstracts), short queries; the corpus is small enough that a vector index is cheap, so the
  speed shown here says nothing about a large store. The corpus is embedded once per machine: the vector arm (and hybrid and composite, if they are ever run) open the same persisted local Qdrant
  folder (system temporary folder, one point per document id, same model and vectors for every arm), and an arm re-embeds only when
  the folder does not hold all 3,633 documents. The arms take the store as their constructor argument, so no change to the hub was
  needed; the temporary folder was deleted after the vector run. Embedding time is not in the per-query seconds. The BM25 arm uses the hub's own tokenizer (lower-case alphanumeric, no stop words, no stemming), not the
  Elasticsearch English analyzer of the BEIR baseline, which is why it differs somewhat from the paper's figure.

### Source: papers (private paper sample)

Do the arms find a known paper in a collection of scientific papers that is already embedded? The paper-collection stage of the
`context-assembler` seat, with queries that are a paper's **title** or a **sentence of its abstract**. The paraphrase stage
(the `paraphrase` source) uses the same corpus with harder queries; the public benchmark is the `nfcorpus` source.

- **Corpus**: a 3,000-paper sample of our research-papers collection (5.0 million papers; abstracts of PubMed, bioRxiv, medRxiv and arXiv
  papers), identified by DOI (`corpus_ids.json`, in sample order: a DOI for 2,642 papers, else a PubMed or preprint id). The sample is the
  first 3,000 usable papers (title of 20 or more characters, abstract of 300 or more, a title not seen before) at or after a fixed point
  in the collection's id order, which is effectively random. We read it, read only, together with the vectors the collection stores;
  **no document is embedded for this stage**. The stored vectors come from Voyage `voyage-3.5-lite`.
- **Cases** (`datasets/papers.json`, committed in full; titles and abstracts are public): 300 papers, all different, drawn with a fixed seed: 150
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
  and `QDRANT_COLLECTION_RESEARCH_PAPERS`) and `VOYAGE_API_KEY`: `esoi run context_assembler --impl bm25`. Without our collection,
  **reproduce it with your own embeddings**: `rebuild_corpus.py` fetches the same papers' titles and abstracts from PubMed and OpenAlex by
  the identifiers in `corpus_ids.json` (in a 60-paper test, 56 matched our stored titles; a few have no abstract at the public sources)
  and with `--embed` embeds them with `voyage-3.5-lite` (about 1.8 million tokens, about $0.04). Without `--embed` only `bm25` runs.
  `export_public_ids.py` and `build_papers_cases.py` are the maintainers' scripts that wrote `corpus_ids.json` and `datasets/papers.json`.
- **Limits**: a known-item check on 3,000 papers is easy for an arm that matches words, so it is a sanity stage that shows an arm does
  not fail here, not which arm is cleverer. The stored vectors may have been made from text slightly different from title plus abstract.

### Source: paraphrase (private paper sample, harder queries)

The harder question of the paper-collection stage: given a short description of a paper in other words, does the arm put that paper in
its first five results? Same 3,000-paper sample of our research-papers collection (identified by DOI in
`../papers/corpus_ids.json`), same stored `voyage-3.5-lite` vectors (no document is embedded), same arms, wiring and pass
rule as `../papers`. Only the query differs.

- **Cases** (`datasets/paraphrase.json`, committed in full; the papers' titles and abstracts are public): the same 300 papers as the known-item stage,
  each with one paraphrase of the abstract's claim, 9 to 26 words, as a person who had not read the paper might type it. Each was written
  once by the cheapest Gemini text model (`gemini-2.5-flash-lite`, prompt in `paraphrase.py`), refused and rewritten up to 3 times if it shared
  a run of 4 consecutive words with the title or abstract (3 of 300 still did after 3 tries and were kept). Writing them took 108,497
  input and 6,008 output tokens, about $0.013 at that model's price ($0.10 and $0.40 per million tokens, `tier_prices.csv`), paid once and
  not part of an arm's row.
- **Pass**, details, queries and cost: as in the known-item stage (300 query embeddings, about $0.0002 for an arm that searches vectors).
- **Order of arms**: `bm25` first; a costlier arm is run only where the cheaper one leaves cases to win.
- **Run**: as in the known-item stage, `esoi run context_assembler --impl bm25` (and `vector`, `hybrid`, `composite`); rebuild
  the corpus from public sources with `../papers/rebuild_corpus.py`. `build_paraphrase_cases.py` regenerates the paraphrases
  (maintainers: it needs the collection and a Gemini key).
- **Limits**: one paraphraser, one pass; the paraphrase can still echo single distinctive words, which favours word matching.

## Results (generated by `results_table.py` from the records)

<!-- results:start -->
No arm is recorded on the pooled case set yet: its papers and paraphrase sources read a private collection, so a run needs that collection's settings. Rows recorded earlier on the public benchmark alone sit in `esoi/results.csv` under their own case hash and are not comparable with the pooled number.
<!-- results:end -->

## Reading the results

- **Selection**: `esoi select context-assembler --promote` did not promote: vector leads at the offline stage but does not meet its
  gate. On the 323 shared queries the two arms disagree on 51, and vector is not shown better than bm25 (exact McNemar, p=0.288), so
  there is no switch; more queries would be needed to settle it.
- **Public sanity check**: BEIR's published BM25 nDCG@10 on NFCorpus is 0.325 (Thakur et al., NeurIPS 2021, Table 2, Elasticsearch
  analyzer); our bm25 arm gets 0.3065 on the same 323 queries, about 6% lower, consistent with the simpler tokenizer. The vector arm's
  model (bge-small-en-v1.5) reports 0.34305 on MTEB's copy of the same test set; ours is 0.3365. Both public numbers are in
  `hubofhubs/registry/hub_evidence.csv`.
