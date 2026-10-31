"""Rebuild cases.json for the paper known-item stage of the context-assembler seat. Maintainers only (needs the pulled sample).

    python3 evaluation/context_assembler_papers/build_cases.py

Positions are drawn from the sample with a fixed seed, all distinct, half titles and half abstract sentences. Each case holds the query
text and the public identifier of its paper (``corpus_ids.json``, written by ``export_public_ids.py``); titles and abstracts are public.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402

QUERIES = 300


def main():
    papers, ids = score.pull(), score.corpus_ids()
    positions = random.Random(score.SEED).sample(range(score.SAMPLE), QUERIES)
    cases = []
    for i, p in enumerate(positions):
        kind = "title" if i < QUERIES // 2 else "sentence"
        query = papers[p]["title"] if kind == "title" else score.sentence_of(papers[p], p)
        cases.append(dict(id=f"q-{i + 1:03d}", kind=kind, stratum=kind, gold=ids[p], query=query))
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases over a sample of {score.SAMPLE} -> {out.name}")


if __name__ == "__main__":
    main()
