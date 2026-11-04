"""Bm25Fielded measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.lexical import Bm25Fielded


def build(meter):
    return adapt(Bm25Fielded, meter)
