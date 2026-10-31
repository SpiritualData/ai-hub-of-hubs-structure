"""Rebuild cases.json for the 150-question stage of the know-the-world seat.

    python3 evaluation/know_the_world_150/build_cases.py

The first 40 cases are exactly the cases of ``evaluation/know_the_world`` (read from its cases.json, so the old rows stay a subset),
and the other 110 are drawn from the remaining LitSearch questions that have quality 2 and exactly one gold paper, with the fixed seed
20261031 + 1 (``random.Random(seed).sample`` of the remaining usable questions in index order). Same source, same matching rule and
same gold-title lookup as the 40-case stage. Standard library only.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "know_the_world"))
import build_cases as base  # noqa: E402

SEED = base.SEED + 1
TOTAL = 150


def main():
    first = json.loads((Path(base.__file__).with_name("cases.json")).read_text(encoding="utf-8"))
    taken = {c["id"] for c in first}
    queries = []
    for offset in range(0, 600, 100):
        queries += [r["row"] for r in base.get("rows", config="query", offset=offset, length=100)["rows"]]
    usable = [dict(index=i, **q) for i, q in enumerate(queries)
              if q["quality"] == 2 and len(q["corpusids"]) == 1 and f"litsearch-{i:03d}" not in taken]
    picked = random.Random(SEED).sample(usable, TOTAL - len(first))
    more = []
    for q in sorted(picked, key=lambda q: q["index"]):
        corpusid = q["corpusids"][0]
        rows = base.get("filter", config="corpus_clean", where=f'"corpusid"={corpusid}', length=1)["rows"]
        more.append(dict(id=f"litsearch-{q['index']:03d}", area=q["query_set"], question=q["query"],
                         gold_title=rows[0]["row"]["title"], gold_corpusid=corpusid))
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(first + more, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(first)} + {len(more)} cases from {len(usable)} remaining usable -> {out.name}")


if __name__ == "__main__":
    main()
