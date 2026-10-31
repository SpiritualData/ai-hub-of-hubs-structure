"""BASELINE: the naive check. Every check holds, whatever the fact says. Zero model calls."""


def build(meter):
    return lambda kind, args: True
