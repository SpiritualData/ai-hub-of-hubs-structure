"""BASELINE: the naive tier pick. The arm with the highest pass rate wins, whatever it costs, priced or not. Zero model calls."""


def build(meter):
    def run(kind, args):
        best = max(args["arms"], key=lambda a: (a["passed"] / a["cases"]) if a["cases"] else 0.0)
        return [best["provider"], best["model"]]
    return run
