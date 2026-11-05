"""LearnedRerank measured on the context-retrieval case set (see hubofhubs/retrieval)."""
from context_retrieval.score import adapt
from hubofhubs.the_intelligence.subconscious.context_retriever.learned import LearnedRerank


def build(meter):
    return adapt(LearnedRerank, meter)
