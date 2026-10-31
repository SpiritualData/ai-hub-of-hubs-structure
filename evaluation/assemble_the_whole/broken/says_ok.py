"""BASELINE: the naive whole. Every seat is reported fine and no variable is looked at. Zero model calls."""


def build(meter):
    return lambda kind, args: "ok"
