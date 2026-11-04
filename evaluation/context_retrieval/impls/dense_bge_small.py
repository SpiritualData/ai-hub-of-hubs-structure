"""DenseBgeSmall measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.dense import DenseBgeSmall


def build(meter):
    return adapt(DenseBgeSmall, meter)
