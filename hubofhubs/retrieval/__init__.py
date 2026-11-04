"""Retrieve the context a task needs from a corpus of files, under a token budget.

One family of arms behind one seat (``retrieve-context``): a lexical first stage over fielded chunks, a dense first stage, their reciprocal
rank fusion, a local feature reranker, graph and history priors, a learned reranker, an abstaining wrapper and a model reranker (recorded and
replayed, never run here). Every arm answers the same call, ``retrieve(query, files, budget_tokens)``, and is scored on one balanced number
(``evaluation/context_retrieval``). Nothing here reads the environment or contacts a service, except the arms that name a model in their
``REQUIRES``.
"""
