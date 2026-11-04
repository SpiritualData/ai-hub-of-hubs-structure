# retrieve-context: pick the pieces of a corpus a task needs within a token budget

*ESOI records kept beside the code in `hubofhubs/retrieval`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

## retrieve-context: pick the pieces of a corpus a task needs within a token budget (`retrieve-context`)

Show a task the context it needs and little else, for any consumer that keeps its knowledge in files.

- Entry call: `hubofhubs.run("retrieve-context", ...)`
- Selected implementation: `abstaining_hybrid`
- Metric: Balanced score of retrieval on file, topic, orientation and no-context requests, with the index size
- Implemented by: [`hubofhubs/retrieval/__init__.py`](__init__.py), [`hubofhubs/retrieval/abstain.py`](abstain.py), [`hubofhubs/retrieval/base.py`](base.py), [`hubofhubs/retrieval/dense.py`](dense.py), [`hubofhubs/retrieval/fusion.py`](fusion.py), [`hubofhubs/retrieval/learned.py`](learned.py), [`hubofhubs/retrieval/lexical.py`](lexical.py), [`hubofhubs/retrieval/units.py`](units.py) and 1 more

## Implementations

| Implementation | Name | Code | Selected |
|---|---|---|---|
| `retrieve-context:bm25_body` | BM25 over chunk text | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| `retrieve-context:bm25_fielded` | BM25F over path, title and body | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| `retrieve-context:bm25_whole_files` | BM25F over whole files | [`hubofhubs/retrieval/lexical.py`](lexical.py) |  |
| `retrieve-context:lsi` | Latent semantic index | [`hubofhubs/retrieval/dense.py`](dense.py) |  |
| `retrieve-context:dense_bge_small` | Dense bge-small vectors | [`hubofhubs/retrieval/dense.py`](dense.py) |  |
| `retrieve-context:hybrid_rrf` | BM25F and dense by rank fusion | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| `retrieve-context:feature_rerank` | Local feature reranker | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| `retrieve-context:feature_rerank_no_priors` | Feature reranker without priors | [`hubofhubs/retrieval/fusion.py`](fusion.py) |  |
| `retrieve-context:learned_rerank` | Learned reranker | [`hubofhubs/retrieval/learned.py`](learned.py) |  |
| `retrieve-context:abstaining_hybrid` | Hybrid that can say nothing | [`hubofhubs/retrieval/abstain.py`](abstain.py) | selected |
| `retrieve-context:abstaining_learned` | Learned reranker that can say nothing | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |
| `retrieve-context:llm_rerank` | Model reranker | [`hubofhubs/retrieval/abstain.py`](abstain.py) |  |

## Metrics

- `metric-retrieve-context`, Balanced score of retrieval on file, topic, orientation and no-context requests, with the index size: leader `abstaining_hybrid`, 127 of 253 cases

## Problems

- `hprob-context-too-broad-or-missing`: A task is shown too much of a codebase, the wrong part of it, or context it never needed, so the model pays for noise or misses the file that matters.

## Ideals

- `hideal-context-needed-and-little-else`: A task is shown the pieces it needs, in order of need, within a budget, and nothing when it needs nothing.

## Where to go next

- Up: [hubofhubs](../README.md)
- Intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
