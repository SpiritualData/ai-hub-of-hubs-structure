"""LatentSemantic measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.the_intelligence.subconscious.context_retriever.dense import LatentSemantic


def build(meter):
    return adapt(LatentSemantic, meter)
