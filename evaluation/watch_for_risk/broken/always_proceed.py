"""BASELINE and the `none` arm: no watch, so every digest gets severity none. Zero model calls."""


def build(meter):
    return lambda kind, args: ["none", False]
