"""BASELINE: a model that never gives a readable reply. Zero model calls; every prompt case fails and Folder View keeps the evidence arm's own picks."""


def build(meter):
    return lambda kind, args: ""
