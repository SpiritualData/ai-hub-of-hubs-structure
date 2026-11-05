"""Bm25Fielded measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.the_intelligence.subconscious.context_retriever.lexical import Bm25Fielded


def build(meter):
    return adapt(Bm25Fielded, meter)
