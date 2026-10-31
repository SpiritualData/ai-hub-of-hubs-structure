"""Rebuild the 3,000-paper corpus from public sources, for anyone who does not have our collection.

    python3 evaluation/context_assembler_papers/rebuild_corpus.py [--out FILE] [--limit N] [--embed]

Reads ``corpus_ids.json`` and fetches each paper's title and abstract from PubMed (E-utilities ``efetch``, by PubMed id) or from OpenAlex
(by DOI, for papers without a PubMed id), in batches. Writes the JSON lines file the stage reads (default: the stage's cache), one paper
per line in sample order: ``id``, ``title``, ``abstract`` and, with ``--embed``, ``vector``. ``--embed`` embeds every abstract once with
the collection's model (Voyage ``voyage-3.5-lite``, input type document, key in ``VOYAGE_API_KEY``): about 1.8 million tokens, about $0.04
at $0.02 per million tokens, so it asks for the cost to be accepted by being given explicitly. Without it the vector, hybrid and composite
arms are not measured and bm25 runs. The text from the public sources can differ slightly from the text our collection stored (markup,
section labels), so a rebuilt corpus is the same papers, not byte-identical text. Standard library only, plus ``voyageai`` for ``--embed``.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402

PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
OPENALEX = "https://api.openalex.org/works"


def get(url, params):
    request = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "hubofhubs-evaluation (open-source research)"})
    for attempt in range(4):
        try:
            return urllib.request.urlopen(request, timeout=120).read()
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"could not fetch {url}")


def pubmed(pmids):
    found = {}
    for start in range(0, len(pmids), 150):
        root = ET.fromstring(get(PUBMED, dict(db="pubmed", id=",".join(pmids[start:start + 150]), retmode="xml")))
        for article in root.iter("PubmedArticle"):
            pmid = article.findtext(".//MedlineCitation/PMID")
            title = "".join(article.find(".//ArticleTitle").itertext()).strip() if article.find(".//ArticleTitle") is not None else ""
            abstract = " ".join("".join(t.itertext()).strip() for t in article.iterfind(".//Abstract/AbstractText"))
            found[pmid] = (title, abstract)
        time.sleep(0.4)   # NCBI allows 3 requests a second without a key
    return found


def openalex(dois):
    found = {}
    for start in range(0, len(dois), 40):
        batch = dois[start:start + 40]
        data = json.loads(get(OPENALEX, {"filter": "doi:" + "|".join("https://doi.org/" + d for d in batch), "per-page": 50,
                                         "select": "doi,title,abstract_inverted_index"}))
        for work in data.get("results", []):
            index = work.get("abstract_inverted_index") or {}
            words = sorted(((pos, word) for word, positions in index.items() for pos in positions))
            found[(work.get("doi") or "").replace("https://doi.org/", "").lower()] = (work.get("title") or "", " ".join(w for _, w in words))
        time.sleep(0.2)
    return found


def main():
    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1]) if "--out" in args else score.CACHE / "sample.jsonl"
    entries = json.loads((Path(score.__file__).with_name("corpus_ids.json")).read_text(encoding="utf-8"))
    if "--limit" in args:
        entries = entries[:int(args[args.index("--limit") + 1])]
    by_pubmed = pubmed([e["pmid"] for e in entries if e["pmid"]])
    by_doi = openalex([e["doi"] for e in entries if not e["pmid"] and e["doi"]])
    papers, missing = [], 0
    for entry in entries:
        title, abstract = by_pubmed.get(entry["pmid"], ("", "")) if entry["pmid"] else by_doi.get(entry["doi"], ("", ""))
        missing += not (title and abstract)
        papers.append(dict(id=entry["id"], title=title, abstract=abstract))
    if "--embed" in args:
        import voyageai
        client = voyageai.Client(api_key=score.setting("voyage"), max_retries=3)
        for start in range(0, len(papers), 64):
            chunk = papers[start:start + 64]
            result = client.embed([score.text_of(p) for p in chunk], model=score.QUERY_MODEL, input_type="document")
            for paper, vector in zip(chunk, result.embeddings):
                paper["vector"] = vector
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(p) for p in papers), encoding="utf-8")
    print(f"{len(papers)} papers written to {out.name}, {missing} without a title and abstract from the public sources")


if __name__ == "__main__":
    main()
