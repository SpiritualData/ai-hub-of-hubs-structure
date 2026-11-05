# Arms in retrieval

*ESOI arms kept in `hubofhubs/retrieval`, generated from the records of the intents that own them by `esoi readmes`. Edit those records, not this page.*

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Hybrid with soft affinity to the request's focus | `context-retriever:abstaining_affinity` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Hybrid with recency, affinity and supersession | `context-retriever:abstaining_aware` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Hybrid behind a hard focus fence | `context-retriever:abstaining_fenced` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Hybrid that can say nothing | `context-retriever:abstaining_hybrid` | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |
| Learned reranker that can say nothing | `context-retriever:abstaining_learned` | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |
| Hybrid that prefers newer items | `context-retriever:abstaining_recency` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| BM25 over chunk text | `context-retriever:bm25_body` | [`hubofhubs/retrieval/lexical.py`](lexical.py) | selected |
| BM25F over path, title and body | `context-retriever:bm25_fielded` | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| BM25F over whole files | `context-retriever:bm25_whole_files` | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| Dense bge-small vectors | `context-retriever:dense_bge_small` | [`hubofhubs/retrieval/dense.py`](dense.py) |  |
| Local feature reranker | `context-retriever:feature_rerank` | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| Feature reranker without priors | `context-retriever:feature_rerank_no_priors` | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| BM25F and dense by rank fusion | `context-retriever:hybrid_rrf` | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| Learned reranker | `context-retriever:learned_rerank` | [`hubofhubs/retrieval/learned.py`](learned.py) |  |
| Scan of the live sources | `context-retriever:live_scan` | [`hubofhubs/retrieval/aware.py`](aware.py) |  |
| Model reranker | `context-retriever:llm_rerank` | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |
| Latent semantic index | `context-retriever:lsi` | [`hubofhubs/retrieval/dense.py`](dense.py) |  |

## Where to go next

- Owning intent: [Processing information for one request](../the_intelligence/README.md)
- Repository: [top README](../../README.md)
