"""BASELINE: the primary provider alone, no router. What a consumer wired to one vendor gets today."""
from provider_failover.score import ask, world


def build(meter):
    def run(kind, args):
        primary, _ = world(args)
        return ask(primary, args)
    return run
