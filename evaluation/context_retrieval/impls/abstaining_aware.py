"""AbstainingAware measured on the context-retrieval case set (see hubofhubs/the_intelligence/subconscious/context_retriever/aware.py)."""
from context_retrieval.score import adapt
from hubofhubs.the_intelligence.subconscious.context_retriever.aware import AbstainingAware


def build(meter):
    return adapt(AbstainingAware, meter)
