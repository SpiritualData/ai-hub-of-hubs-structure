# Context Retriever

*ESOI records kept beside the code in `hubofhubs/the_intelligence/subconscious/context_retriever`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The information a request needs is found and prepared before the Mind asks for it, from the system's own cards, its files and what comes to mind unasked.

These are the solutions of [Finding and preparing information for the Mind](../README.md).

## How the solutions fit together

This part finds and prepares information before it is asked for. Cards From Files builds cards from the files of the system. Context Retriever picks the cards and file units that bear on the request. Intuition offers what occurs to the system unasked.

## Context Retriever (`context-retriever`)

Pick, from a corpus of files, cards or memory, the pieces of text a task needs within a token budget.

- Entry call: `hubofhubs.run("context-retriever", ...)`
- Selected implementation: BM25 over chunk text (`bm25_body`)
- Metric: Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../../critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../../critical_thinking/goal_completion/goal_completion.py) and 136 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| BM25 over chunk text | `context-retriever:bm25_body` | [`hubofhubs/the_intelligence/subconscious/context_retriever/lexical.py`](lexical.py) | selected |
| BM25F over path, title and body | `context-retriever:bm25_fielded` | [`hubofhubs/the_intelligence/subconscious/context_retriever/lexical.py`](lexical.py) |  |
| BM25F over whole files | `context-retriever:bm25_whole_files` | [`hubofhubs/the_intelligence/subconscious/context_retriever/lexical.py`](lexical.py) |  |
| Latent semantic index | `context-retriever:lsi` | [`hubofhubs/the_intelligence/subconscious/context_retriever/dense.py`](dense.py) |  |
| Dense bge-small vectors | `context-retriever:dense_bge_small` | [`hubofhubs/the_intelligence/subconscious/context_retriever/dense.py`](dense.py) |  |
| BM25F and dense by rank fusion | `context-retriever:hybrid_rrf` | [`hubofhubs/the_intelligence/subconscious/context_retriever/fusion.py`](fusion.py) |  |
| Local feature reranker | `context-retriever:feature_rerank` | [`hubofhubs/the_intelligence/subconscious/context_retriever/fusion.py`](fusion.py) |  |
| Feature reranker without priors | `context-retriever:feature_rerank_no_priors` | [`hubofhubs/the_intelligence/subconscious/context_retriever/fusion.py`](fusion.py) |  |
| Learned reranker | `context-retriever:learned_rerank` | [`hubofhubs/the_intelligence/subconscious/context_retriever/learned.py`](learned.py) |  |
| Hybrid that can say nothing | `context-retriever:abstaining_hybrid` | [`hubofhubs/the_intelligence/subconscious/context_retriever/abstain.py`](abstain.py) |  |
| Learned reranker that can say nothing | `context-retriever:abstaining_learned` | [`hubofhubs/the_intelligence/subconscious/context_retriever/abstain.py`](abstain.py) |  |
| Model reranker | `context-retriever:llm_rerank` | [`hubofhubs/the_intelligence/subconscious/context_retriever/abstain.py`](abstain.py) |  |
| Hybrid that prefers newer items | `context-retriever:abstaining_recency` | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Hybrid with soft affinity to the request's focus | `context-retriever:abstaining_affinity` | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Hybrid with recency, affinity and supersession | `context-retriever:abstaining_aware` | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Hybrid behind a hard focus fence | `context-retriever:abstaining_fenced` | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |
| Scan of the live sources | `context-retriever:live_scan` | [`hubofhubs/the_intelligence/subconscious/context_retriever/aware.py`](aware.py) |  |

## Metrics

- Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources (`metric-context-retriever`): leader `bm25_body`, 203 of 395 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Finding and preparing information for the Mind](../README.md)
- Repository: [top README](../../../../README.md)
