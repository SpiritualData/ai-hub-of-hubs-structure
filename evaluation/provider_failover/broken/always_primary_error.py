"""BASELINE: a router that never asks the secondary provider, so any primary failure is the answer."""
from provider_failover.score import ask, world


def build(meter):
    def run(kind, args):
        primary, _ = world(args)
        return ask(primary, args)
    return run
