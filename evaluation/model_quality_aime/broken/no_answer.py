"""BASELINE: a model that never finishes with a final answer line. Zero model calls."""


def build(meter):
    return lambda kind, args: "I am not sure."
