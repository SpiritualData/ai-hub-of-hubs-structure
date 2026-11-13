"""ABLATION: no answer check, as a run was before. Zero model calls; every answer passes, so every drift and every half answer is missed."""


def build(meter):
    return lambda kind, args: {"passed": True, "parts": []}
