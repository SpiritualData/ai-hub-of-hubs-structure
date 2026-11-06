"""BASELINE: the naive whole. It answers every request with the word done, reports no steps and spends nothing: a whole that claims completion it did not do."""


def build(meter):
    return lambda kind, args: {"answer": "done", "note": "", "steps": [], "calls": 0}
