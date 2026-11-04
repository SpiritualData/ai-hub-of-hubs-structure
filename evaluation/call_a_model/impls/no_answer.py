"""A model that never finishes with a final answer line. Zero model calls."""
ALTERNATIVE = True   # a diagnostic bound, ranked on the same number as every arm and never excluded by a mark


def build(meter):
    return lambda kind, args: "I am not sure."
