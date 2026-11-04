# Context retriever

*ESOI records kept beside the code in `hubofhubs/retrieval`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

## Context retriever (`retrieve-context`)

Show a task the context it needs and little else, for any consumer that keeps its knowledge in files.

- Entry call: `hubofhubs.run("retrieve-context", ...)`
- Selected implementation: `abstaining_hybrid`
- Metric: Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources
- Implemented by: [`hubofhubs/retrieval/__init__.py`](__init__.py), [`hubofhubs/retrieval/abstain.py`](abstain.py), [`hubofhubs/retrieval/aware.py`](aware.py), [`hubofhubs/retrieval/base.py`](base.py), [`hubofhubs/retrieval/dense.py`](dense.py), [`hubofhubs/retrieval/fusion.py`](fusion.py), [`hubofhubs/retrieval/learned.py`](learned.py), [`hubofhubs/retrieval/lexical.py`](lexical.py) and 3 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| BM25 over chunk text | `retrieve-context:bm25_body` | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| BM25F over path, title and body | `retrieve-context:bm25_fielded` | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| BM25F over whole files | `retrieve-context:bm25_whole_files` | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| Latent semantic index | `retrieve-context:lsi` | [`hubofhubs/retrieval/dense.py`](dense.py) |  |
| Dense bge-small vectors | `retrieve-context:dense_bge_small` | [`hubofhubs/retrieval/dense.py`](dense.py) |  |
| BM25F and dense by rank fusion | `retrieve-context:hybrid_rrf` | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| Local feature reranker | `retrieve-context:feature_rerank` | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| Feature reranker without priors | `retrieve-context:feature_rerank_no_priors` | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| Learned reranker | `retrieve-context:learned_rerank` | [`hubofhubs/retrieval/learned.py`](learned.py) |  |
| Hybrid that can say nothing | `retrieve-context:abstaining_hybrid` | [`hubofhubs/retrieval/abstain.py`](abstain.py) | selected |
| Learned reranker that can say nothing | `retrieve-context:abstaining_learned` | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |
| Model reranker | `retrieve-context:llm_rerank` | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |
| Hybrid that prefers newer items | `retrieve-context:abstaining_recency` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Hybrid with soft affinity to the request's focus | `retrieve-context:abstaining_affinity` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Hybrid with recency, affinity and supersession | `retrieve-context:abstaining_aware` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Hybrid behind a hard focus fence | `retrieve-context:abstaining_fenced` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Scan of the live sources | `retrieve-context:live_scan` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |

## Metrics

- Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources (`metric-retrieve-context`): leader `bm25_body`, 203 of 395 cases

## Problems

- `hprob-context-too-broad-or-missing`: A task is shown too much of a codebase, the wrong part of it, or context it never needed, so the model pays for noise or misses the file that matters.

## Ideals

- The context a task needs, and little else (`hideal-context-needed-and-little-else`): A task is shown the pieces it needs, in order of need, within a budget, and nothing when it needs nothing.

## Where to go next

- Up: [hubofhubs](../README.md)
- Intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
