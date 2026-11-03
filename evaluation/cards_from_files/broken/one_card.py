"""Naive baseline: every file in one card, in walk order. The cases must make it lose to the per-file floor."""


def build(meter):
    return lambda kind, args: []
