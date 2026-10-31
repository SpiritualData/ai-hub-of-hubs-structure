"""Rebuild cases.json for the search-backend seat from the public SimpleQA test set (MIT, OpenAI simple-evals).

    python3 evaluation/search_backend/build_cases.py [path to simple_qa_test_set.csv]

With no path the file is downloaded from the public URL below. The sample is fixed: seed 20261031, 40 questions drawn from
those whose metadata names at least one source URL (none containing the text "/home", which the repository's path-hygiene check would flag), spread over the dataset's topics. Standard library only.
"""
import ast
import csv
import json
import random
import sys
import urllib.request
from pathlib import Path

URL = "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"
SEED = 20261031
COUNT = 40


def main():
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        text = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8")
    rows = list(csv.DictReader(text.splitlines(keepends=True)))
    usable = []
    for index, row in enumerate(rows):
        meta = ast.literal_eval(row["metadata"])
        urls = [u for u in dict.fromkeys(meta.get("urls", [])) if u.startswith("http")]
        if urls and not any("/home" in u for u in urls):   # such a URL trips the repository's machine-path hygiene check
            usable.append(dict(index=index, topic=meta.get("topic", ""), question=row["problem"], answer=row["answer"], urls=urls))
    rng = random.Random(SEED)
    picked = rng.sample(usable, COUNT)
    cases = [dict(id=f"simpleqa-{c['index']:04d}", area=c["topic"], question=c["question"], gold_urls=c["urls"], answer=c["answer"])
             for c in sorted(picked, key=lambda c: c["index"])]
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases from {len(usable)} usable of {len(rows)} -> {out.name}")


if __name__ == "__main__":
    main()
