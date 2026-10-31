# context_assembler

Does the arm put a document that answers the query in its first five results? Four arms of the `context-assembler` seat
(`bm25`, `vector`, `hybrid`, `composite`), the memory-and-recall sub-seat of the hub, compared on the same queries.

- **Cases** (`cases.json`): the 323 test queries of the public BEIR **NFCorpus** benchmark (medical questions from a nutrition
  site, judged against 3,633 PubMed abstracts, relevance grades 1 and 2). That is the whole official test split, not a sample, so
  the figures can be set beside the BEIR paper. The file holds ids and grades only.
- **Corpus**: the whole NFCorpus corpus (3,633 documents, every gold document plus all the benchmark's distractors); nothing is
  sub-sampled. The arms see the same text: title, blank line, abstract.
- **License, stated honestly.** The BEIR code is Apache-2.0; the Hugging Face card for the BEIR copy says CC BY-SA 4.0; the BEIR
  paper (appendix E) says NFCorpus reports no license in the paper or repository; the NFCorpus authors say "free to use for
  academic purposes" and point to the NutritionFacts.org terms for any other use. Because redistribution is not allowed by any of
  these, **this repository commits only ids and grades**. `score.py` downloads the zip from the official BEIR URL on first use,
  refuses it unless its sha256 is `efe5be03...71b0b` (full value in `score.py`), and caches it in the system temporary folder.
- **Pass**: at least one relevant document in the first 5 ids the arm ranks. `aggregate` also prints nDCG@10 (gain = grade,
  discount log2(rank + 1), as BEIR's `ndcg_cut_10`) and recall@10; `aggregate` returns them and `esoi run --record` writes them into the row's `details`. `results_table.py` builds the table below from the records.
- **Arms and wiring** (all with 10 hits, no model provider: no query rewriting, no review, no consolidation, so no model call
  and $0): `bm25` is the BM25 content store over one `.txt` file per document; `vector` is the vector assembler over a local
  Qdrant folder embedded with `BAAI/bge-small-en-v1.5` (fastembed, 4 ONNX threads, the hub's default model); `hybrid` fuses
  those two by reciprocal rank; `composite` runs both and concatenates their lists (bm25 first). Rank is read from `card_ids`,
  except for `vector`, whose `card_ids` are sorted by id by design, so its `effective_score` order is used.
- **Free stage**: `PYTHONPATH=.:../evolvable-structure/implementations/python OMP_NUM_THREADS=4 python3 -m esoi run context_assembler --impl bm25`
  (and `vector`, `hybrid`, `composite`); add `--record` to log it. Rebuild `cases.json` with `build_cases.py`.
- **Limits**: one domain (biomedical abstracts), short queries; the corpus is small enough that a vector index is cheap, so the
  speed shown here says nothing about a large store. The corpus is embedded once: the vector, hybrid and composite arms open the same persisted local Qdrant
  folder (system temporary folder, one point per document id, same model and vectors for every arm), and an arm re-embeds only when
  the folder does not hold all 3,633 documents. The arms take the store as their constructor argument, so no change to the hub was
  needed. Embedding time is not in the per-query seconds. The BM25 arm uses the hub's own tokenizer (lower-case alphanumeric, no stop words, no stemming), not the
  Elasticsearch English analyzer of the BEIR baseline, which is why it differs somewhat from the paper's figure.
