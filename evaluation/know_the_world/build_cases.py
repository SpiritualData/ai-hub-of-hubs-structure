"""Rebuild cases.json for the know-the-world seat from LitSearch (MIT, github.com/princeton-nlp/LitSearch; data on Hugging Face).

    python3 evaluation/know_the_world/build_cases.py

LitSearch has 597 literature-search questions about recent ML and NLP papers, each with the corpus id of its gold paper(s).
The sample is fixed: seed 20261031, 40 questions that have quality 2 (the dataset's top rating) and exactly one gold paper,
spread over the dataset's query sets. The gold paper's title is read from the dataset's ``corpus_clean`` table (it carries
titles, not DOIs, so the check is by exact title). Standard library only; the Hugging Face dataset server is the source.
"""
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SERVER = "https://datasets-server.huggingface.co"
DATASET = "princeton-nlp/LitSearch"
SEED = 20261031
COUNT = 40


def get(path, **params):
    url = f"{SERVER}/{path}?" + urllib.parse.urlencode(dict(dataset=DATASET, split="full", **params))
    for attempt in range(10):
        try:
            body = json.loads(urllib.request.urlopen(url, timeout=30).read())
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)   # the server answers 500 now and then and succeeds on a retry
            continue
        if "error" not in body or "loading" not in body["error"]:
            return body
        time.sleep(10)
    raise RuntimeError("the dataset index did not load")


def main():
    queries = []
    for offset in range(0, 600, 100):
        queries += [r["row"] for r in get("rows", config="query", offset=offset, length=100)["rows"]]
    usable = [dict(index=i, **q) for i, q in enumerate(queries) if q["quality"] == 2 and len(q["corpusids"]) == 1]
    picked = random.Random(SEED).sample(usable, COUNT)
    cases = []
    for q in sorted(picked, key=lambda q: q["index"]):
        corpusid = q["corpusids"][0]
        rows = get("filter", config="corpus_clean", where=f'"corpusid"={corpusid}', length=1)["rows"]
        cases.append(dict(id=f"litsearch-{q['index']:03d}", area=q["query_set"], question=q["query"],
                          gold_title=rows[0]["row"]["title"], gold_corpusid=corpusid))
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases from {len(usable)} usable of {len(queries)} -> {out.name}")


if __name__ == "__main__":
    main()
