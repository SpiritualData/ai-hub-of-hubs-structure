"""LearnedRerank measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.retrieval.learned import LearnedRerank


def build(meter):
    return adapt(LearnedRerank, meter)
