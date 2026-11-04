"""No arm. The folder is left as it was, so every case fails its check. No model call."""
ALTERNATIVE = True   # a diagnostic bound, ranked on the same number as every arm and never excluded by a mark


def build(meter):
    return lambda kind, args: None
