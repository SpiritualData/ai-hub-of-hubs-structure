"""Score one hub solution-relevance case with the esoi library's shared scorer (recall of the gold solutions, a precision floor);
this metric builds on the library's metric-solution-relevance and adds only the hub's own cases."""
from esoi.understanding.solution_relevance.relevance_cases import aggregate, score_case

__all__ = ["aggregate", "score_case"]
