"""BASELINE and the `none` arm: no overseer, so every digest gets `proceed`. Zero model calls."""


def build(meter):
    return lambda kind, args: ["proceed", False]
