"""BASELINE: no arm. The folder is left as it was, so every case fails its check. No model call."""


def build(meter):
    return lambda kind, args: None
