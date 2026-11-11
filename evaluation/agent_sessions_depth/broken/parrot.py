"""BASELINE, the naive agent a first draft would write: it reports the goal back as its answer and says it met it. Zero model calls."""


class Reply:
    def __init__(self, text):
        self.output, self.met, self.error, self.cost_usd = text, True, "", 0.0


def build(meter):
    return lambda kind, args: Reply(args["goal"])
