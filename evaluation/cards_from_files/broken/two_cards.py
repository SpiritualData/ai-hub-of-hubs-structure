"""Naive baseline: two cards, the test files and the rest, each in walk order. The cases must make it lose to the per-file floor."""


def build(meter):
    return lambda kind, args: []
