"""Naive baseline: one card per folder, files in walk order. The cases must make it lose to the per-file floor."""


def build(meter):
    return lambda kind, args: []
