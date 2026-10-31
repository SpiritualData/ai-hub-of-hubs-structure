"""Write ``corpus_ids.json``: the public identifier of each paper of the 3,000-paper sample, in sample order. Maintainers only (reads the collection).

    python3 evaluation/context_assembler_papers/export_public_ids.py

Each entry is ``{"id", "doi", "pmid"}``: ``id`` is the DOI when the paper has one (``doi:10.xxxx/...``), else its PubMed id
(``pmid:...``), else the arXiv, bioRxiv or medRxiv identifier the collection holds. Nothing internal (point ids, internal fields, server
addresses) is written. The entries are matched to the sample by title so that a different collection order cannot shift them silently.
"""
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402


def identifiers(metadata, source):
    meta = ast.literal_eval(metadata) if isinstance(metadata, str) and metadata.startswith("{") else (metadata or {})
    original = str(meta.get("original_id") or "").strip()
    doi = str(meta.get("doi") or "").strip().lower()
    pmid = original if source == "pubmed" and original.isdigit() else ""
    if not doi and source in ("biorxiv", "medrxiv") and original.startswith("10."):
        doi = original.lower()
    arxiv = original if source == "arxiv" else ""
    ident = f"doi:{doi}" if doi else f"pmid:{pmid}" if pmid else f"arxiv:{arxiv}" if arxiv else ""
    return dict(id=ident, doi=doi, pmid=pmid)


def main():
    from qdrant_client import QdrantClient
    sample = score.pull()
    wanted = {p["id"]: n for n, p in enumerate(sample)}
    client = QdrantClient(url=score.setting("url"), api_key=score.setting("key"), timeout=120)
    found = {}
    offset = score.OFFSET
    while len(found) < len(wanted) and offset is not None:
        points, offset = client.scroll(score.setting("collection"), limit=256, offset=offset, with_payload=["metadata", "source", "title"], with_vectors=False)
        for point in points:
            if str(point.id) in wanted:
                found[wanted[str(point.id)]] = identifiers(point.payload.get("metadata"), point.payload.get("source"))
    entries = [found[n] for n in range(len(sample))]
    missing = [n for n, e in enumerate(entries) if not e["id"]]
    ids = [e["id"] for e in entries]
    if missing or len(set(ids)) != len(ids):
        raise SystemExit(f"{len(missing)} papers without a public identifier, {len(ids) - len(set(ids))} duplicates")
    (Path(__file__).with_name("corpus_ids.json")).write_text(json.dumps(entries, indent=0) + "\n", encoding="utf-8")
    print(f"{len(entries)} identifiers: {sum(e['id'].startswith('doi:') for e in entries)} DOI, {sum(e['id'].startswith('pmid:') for e in entries)} PubMed id, rest preprint ids")


if __name__ == "__main__":
    main()
