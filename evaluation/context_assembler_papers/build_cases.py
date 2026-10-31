"""Rebuild cases.json for the private-corpus stage of the context-assembler seat.

    python3 evaluation/context_assembler_papers/build_cases.py

The cases hold no text and no id of any paper: only a position in the pulled sample and the kind of query to make from the paper at
that position (``title`` or ``sentence``). Positions are drawn with a fixed seed, all distinct, half of each kind. Standard library only.
"""
import json
import random
from pathlib import Path

SEED = 20261031
SAMPLE = 3000
QUERIES = 300


def main():
    positions = random.Random(SEED).sample(range(SAMPLE), QUERIES)
    cases = [dict(id=f"q-{i + 1:03d}", position=p, kind="title" if i < QUERIES // 2 else "sentence", stratum="title" if i < QUERIES // 2 else "sentence")
             for i, p in enumerate(positions)]
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases over a sample of {SAMPLE} -> {out.name}")


if __name__ == "__main__":
    main()
