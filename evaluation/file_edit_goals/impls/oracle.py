"""VALIDITY check of the check: writes the benchmark's reference solution, so every case must pass. No model call."""
from pathlib import Path


def build(meter):
    def run(kind, args):
        (Path(args["root"]) / "solution.py").write_text(args["case"]["solution"], encoding="utf-8")
    return run
