"""Rebuild cases.json for the context-assembler seat from the public BEIR NFCorpus test split.

    python3 evaluation/context_assembler/build_cases.py

Only ids and the relevance grades are written (query id, and the corpus document ids with their grade 1 or 2), never the query or
document text: NFCorpus is free for academic use but states no redistribution license, so the text is downloaded at run time from
the official BEIR URL by ``score.py`` and checked against the sha256 below. Every query of the test split with at least one judged
relevant document is a case (the whole split, so the figures are comparable with the BEIR paper). Standard library only.
"""
import json
from pathlib import Path

import score

SPLIT = "test"


def main():
    data = score.dataset()
    grades = {}
    for line in data["qrels"].splitlines()[1:]:
        query, doc, grade = line.split("\t")
        if int(grade) > 0:
            grades.setdefault(query, {})[doc] = int(grade)
    cases = [dict(id=q, relevant=dict(sorted(g.items()))) for q, g in sorted(grades.items())]
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases, {len(data['corpus'])} documents in the corpus -> {out.name}")


if __name__ == "__main__":
    main()
