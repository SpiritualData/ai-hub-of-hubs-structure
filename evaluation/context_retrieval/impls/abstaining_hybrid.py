"""AbstainingHybrid measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.abstain import AbstainingHybrid


def build(meter):
    return adapt(AbstainingHybrid, meter)
