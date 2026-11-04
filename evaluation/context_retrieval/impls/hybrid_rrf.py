"""HybridRrf measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.fusion import HybridRrf


def build(meter):
    return adapt(HybridRrf, meter)
