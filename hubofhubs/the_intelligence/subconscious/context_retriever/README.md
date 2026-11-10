# Context Retriever

**Purpose:** Pick, from a corpus of files, cards or memory, the pieces of text a task needs within a token budget.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Finding and preparing information for the Mind](../README.md) > Context Retriever

Part of [Finding and preparing information for the Mind](../README.md)

## Context Retriever (`context-retriever`)

- Out of scope: Formatting the picked text (the renderer where the picks are used does that) and offering what is not asked for (Intuition does that).
- Delegates to: the-intuition
- Entry call: `hubofhubs.run("context-retriever", ...)`
- Selected implementation: BM25 over chunk text (`bm25_body`)
- Metric: Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 203 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| BM25 over chunk text | `context-retriever:bm25_body` | Okapi BM25 over each chunk's text alone: the plain keyword search every other arm is compared with. | [`hubofhubs/the_intelligence/subconscious/context_retriever/lexical.py`](lexical.py) | selected |
| BM25F over path, title and body | `context-retriever:bm25_fielded` | BM25 over three fields of each chunk (the file path and a generated descriptor, the chunk's names and docstring, its text) weighted 2, 3 and 1. | [`hubofhubs/the_intelligence/subconscious/context_retriever/lexical.py`](lexical.py) |  |
| BM25F over whole files | `context-retriever:bm25_whole_files` | The same fielded index with a whole file as the unit, so a file costs all its tokens. | [`hubofhubs/the_intelligence/subconscious/context_retriever/lexical.py`](lexical.py) |  |
| Latent semantic index | `context-retriever:lsi` | TF-IDF over chunks projected to 128 dimensions by a truncated SVD, cosine in that space. | [`hubofhubs/the_intelligence/subconscious/context_retriever/dense.py`](dense.py) |  |
| Dense bge-small vectors | `context-retriever:dense_bge_small` | Cosine over local bge-small vectors of each chunk's first 900 characters, cached on disk by text. | [`hubofhubs/the_intelligence/subconscious/context_retriever/dense.py`](dense.py) |  |
| BM25F and dense by rank fusion | `context-retriever:hybrid_rrf` | The fielded keyword ranking and the dense ranking fused by reciprocal rank (k = 60). | [`hubofhubs/the_intelligence/subconscious/context_retriever/fusion.py`](fusion.py) |  |
| Local feature reranker | `context-retriever:feature_rerank` | The top 100 of the hybrid plus the neighbours of its best hits, reranked by a fixed linear mix of eleven features (fused rank, BM25, cosine, term cover, name and path matches, import and co-change neighbours, recency, length). | [`hubofhubs/the_intelligence/subconscious/context_retriever/fusion.py`](fusion.py) |  |
| Feature reranker without priors | `context-retriever:feature_rerank_no_priors` | The same reranker with the link, co-change and recency features off. | [`hubofhubs/the_intelligence/subconscious/context_retriever/fusion.py`](fusion.py) |  |
| Learned reranker | `context-retriever:learned_rerank` | Logistic regression over the same features, trained on the corpus's own history (past commit subjects as queries, the files they changed as relevant), split in time from the test cases. | [`hubofhubs/the_intelligence/subconscious/context_retriever/learned.py`](learned.py) |  |
| Hybrid that can say nothing | `context-retriever:abstaining_hybrid` | The plain hybrid returning an empty list when its confidence (best cosine and term cover) is under a floor set on validation requests. | [`hubofhubs/the_intelligence/subconscious/context_retriever/abstain.py`](abstain.py) |  |
| Learned reranker that can say nothing | `context-retriever:abstaining_learned` | The learned reranker behind the same confidence floor. | [`hubofhubs/the_intelligence/subconscious/context_retriever/abstain.py`](abstain.py) |  |
| Model reranker | `context-retriever:llm_rerank` | A model names the needed ones among the top 30 of the learned reranker (path and 240 characters each). Paid: one call per request; recorded and replayed through a cassette, not run in this repository. | [`hubofhubs/the_intelligence/subconscious/context_retriever/abstain.py`](abstain.py) |  |
| Hybrid that prefers newer items | `context-retriever:abstaining_recency` | The abstaining hybrid with a recency factor: an item loses up to a fifth of its score by its age relative to the request (half-life 180 days). Reads the item timestamps and the request time; items without them rank as before. | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Hybrid with soft affinity to the request's focus | `context-retriever:abstaining_affinity` | The abstaining hybrid with soft affinity (hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.affinity_tags): an item at home in the request's focus times 1.3, an item from elsewhere times 0.8, never hidden. | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Hybrid with recency, affinity and supersession | `context-retriever:abstaining_aware` | Recency and soft affinity together, and of two near-identical items from different times the older one is halved (a fact updated since). | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Hybrid behind a hard focus fence | `context-retriever:abstaining_fenced` | The hard-fence comparison: items outside the request's focus are removed from the candidates, as a scope fence would. | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Scan of the live sources | `context-retriever:live_scan` | The diagnostic bound for source access: no index, every request reads every source and ranks whole files by how often the request's terms occur. | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |

## Metrics

- Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources (`metric-context-retriever`): leader `bm25_body`, 203 of 395 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Finding and preparing information for the Mind](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
