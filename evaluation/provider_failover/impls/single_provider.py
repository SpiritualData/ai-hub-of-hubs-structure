"""The primary provider alone, no router: what a consumer wired to one vendor gets today."""
ALTERNATIVE = True   # a diagnostic bound, ranked on the same number as every arm and never excluded by a mark
from provider_failover.score import ask, world


def build(meter):
    def run(kind, args):
        primary, _ = world(args)
        return ask(primary, args)
    return run
