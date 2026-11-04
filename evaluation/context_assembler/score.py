"""Scores a context-assembler arm with one number over three kinds of query: does a relevant document come back in the first five.

One component, one balanced score (accuracy, cost and time by ``[balance.context_assembler]`` in ``esoi.toml``). The case set pools the
sources named in ``mix.py``, each a file of ``datasets/`` and a module that knows its corpus and its pass rule:

* ``nfcorpus`` (``nfcorpus.py``): the 323 test queries of the public BEIR NFCorpus benchmark, judged against its 3,633 abstracts.
* ``papers`` (``papers.py``): 300 papers of a 3,000-paper sample of a private collection, found by their title or one abstract sentence.
* ``paraphrase`` (``paraphrase.py``): the same sample, found by a paraphrase of the abstract's claim.

A source is a case source and never a stage or a leaderboard of its own: every arm is scored on all of them in one run, and the details
report each source's raw pass count. The private sources read a collection that is not published, so a run without its settings stops
with ``not measured`` instead of scoring only the public part (that would be another case set under the same name).
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_assembler import mix, nfcorpus, papers, paraphrase  # noqa: E402

PRIVATE = ("papers", "paraphrase")


def load_cases():
    """The pooled case set: ``mix.MIX`` cases of each source, each carrying its ``source`` (and a ``stratum`` for ``--sample``)."""
    pools = dict(nfcorpus=[dict(c, stratum="nfcorpus") for c in nfcorpus.load_cases()], papers=papers.load_cases(),
                 paraphrase=paraphrase.load_cases())
    return [dict(case, source=source) for source, count in mix.MIX.items() for case in pools[source][:count]]


def adapt(implementation, meter):
    """Build the arm once per corpus: one over the public benchmark and one over the paper sample (the queries of both private sources
    are embedded together, once). Returns ``run(case)``, which answers with the ranking of the case's own source."""
    public = nfcorpus.adapt(implementation, meter)
    private = papers.adapt(implementation, meter, cases=papers.load_cases() + paraphrase.load_cases())

    def run(case):
        return public(case["id"]) if case["source"] == "nfcorpus" else private(case)
    return run


def score_case(fn, case):
    """The source's own pass rule over the ranking ``fn`` gives for the case."""
    got = fn(case)
    source = case["source"]
    row = nfcorpus.score_case(lambda query_id: got, case) if source == "nfcorpus" else papers.score_case(lambda c: got, case)
    if source == "paraphrase" and not row["ok"]:
        row["note"] = f"paraphrase query: not in the top {papers.PASS_AT}"
    row["source"] = source
    return row


def aggregate(rows):
    """The details of a run: each source's passed over run, the two secondary numbers over every case and the sample's hash."""
    out = {}
    for source in mix.MIX:
        mine = [r for r in rows if r.get("source") == source]
        if mine:
            out[f"{source}_passed"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    out.update(ndcg_at_10=round(statistics.mean(r["ndcg"] for r in rows), 4), recall_at_10=round(statistics.mean(r["recall"] for r in rows), 4))
    digest = getattr(papers.adapt, "digest", "")
    return dict(out, sample_sha=digest) if digest else out
