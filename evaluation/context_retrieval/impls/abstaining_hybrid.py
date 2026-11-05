"""AbstainingHybrid measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.the_intelligence.subconscious.context_retriever.abstain import AbstainingHybrid


def build(meter):
    return adapt(AbstainingHybrid, meter)
