"""AbstainingAware measured on the context-retrieval case set (see hubofhubs/retrieval/aware.py)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.aware import AbstainingAware


def build(meter):
    return adapt(AbstainingAware, meter)
