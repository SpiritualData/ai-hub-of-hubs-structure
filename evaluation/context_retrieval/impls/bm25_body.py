"""Bm25Body measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.the_intelligence.subconscious.context_retriever.lexical import Bm25Body


def build(meter):
    return adapt(Bm25Body, meter)
