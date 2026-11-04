"""Bm25WholeFiles measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.lexical import Bm25WholeFiles


def build(meter):
    return adapt(Bm25WholeFiles, meter)
