"""Item metadata, the request's time and focus, the metadata-aware arms and the source meter, on tiny corpora: no model, no network."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation"))

from hubofhubs.the_intelligence.subconscious.context_retriever.aware import (
    AbstainingAffinity, AbstainingAware, AbstainingFenced, AbstainingRecency, LiveScan)
from hubofhubs.the_intelligence.subconscious.context_retriever.lexical import Bm25Fielded
from hubofhubs.the_intelligence.subconscious.context_retriever.units import age_days, build_corpus, digest_of, parse_time

FILES = {"old.txt": "The standing desk is blue.", "new.txt": "The standing desk is green now.", "other.txt": "The garden has tulips."}
META = {"old.txt": dict(kind="message", author_role="requester", timestamp="2023-01-01T10:00:00", affinity_tags=["repo:a"], scope_tags=["owner:1"]),
        "new.txt": dict(kind="message", author_role="requester", timestamp="2023-06-01T10:00:00", affinity_tags=["repo:b"], scope_tags=["owner:1"]),
        "other.txt": dict(kind="note", timestamp="2023-06-02", affinity_tags=["repo:a"], scope_tags=["owner:2"])}


class Inner:
    """Stands for the hybrid: the old message scores a little higher than the new one (units are in path order: new 0, old 1, other 2) and they are alike."""
    class dense:
        matrix = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

    def scores(self, query):
        return {1: 1.0, 0: 0.95, 2: 0.2}


def arm(kind):
    a = kind(inner=Inner())
    a.corpus = build_corpus(FILES, meta=META)
    a.confidence = lambda query: 1.0
    return a


def order(a, request):
    hits = a.retrieve("standing desk", budget_tokens=4000, request=request)
    return [h.file for h in hits]


def test_time_parsing_and_age():
    assert parse_time("2023-06-01") == parse_time("2023-06-01T00:00:00Z") and parse_time("nonsense") is None and parse_time(None) is None
    assert age_days("2023-01-01", "2023-01-11") == 10.0 and age_days(None, "2023-01-11") is None


def test_metadata_is_optional_and_leaves_the_digest_of_a_corpus_without_it_unchanged():
    assert digest_of(FILES, [], "chunk") == digest_of(FILES, [], "chunk", None) == digest_of(FILES, [], "chunk", {})
    assert digest_of(FILES, [], "chunk", META) != digest_of(FILES, [], "chunk")
    corpus = build_corpus(FILES, meta=META)
    assert corpus.meta_of("old.txt")["kind"] == "message" and build_corpus(FILES).meta_of("old.txt") == {}


def test_an_arm_that_ignores_metadata_ranks_the_same_with_or_without_it():
    plain, withmeta = Bm25Fielded(), Bm25Fielded()
    a = [h.file for h in plain.retrieve("standing desk", FILES)]
    b = [h.file for h in withmeta.retrieve("standing desk", FILES, meta=META, request={"timestamp": "2023-07-01"})]
    assert a == b


def test_recency_puts_the_newer_of_two_equal_matches_first():
    assert order(arm(AbstainingRecency), {"timestamp": "2023-07-01"})[:2] == ["new.txt", "old.txt"]
    assert order(arm(AbstainingRecency), {})[:2] == ["old.txt", "new.txt"]          # no request time: no age, the plain order stays


def test_soft_affinity_prefers_the_focus_but_hides_nothing_while_the_fence_does():
    assert order(arm(AbstainingAffinity), {})[0] == "old.txt"
    assert order(arm(AbstainingAffinity), {"affinity_tags": ["repo:b"]})[0] == "new.txt"
    assert "old.txt" in order(arm(AbstainingAffinity), {"affinity_tags": ["repo:b"]})
    assert "old.txt" not in order(arm(AbstainingFenced), {"affinity_tags": ["repo:b"]})
    assert order(arm(AbstainingFenced), {}) != []                                     # no focus, nothing is fenced


def test_the_newer_of_two_near_identical_facts_supersedes_the_older():
    assert order(arm(AbstainingAware), {"timestamp": "2023-07-01"})[:2] == ["new.txt", "old.txt"]
    a = arm(AbstainingAware)
    a.corpus = build_corpus(FILES)                                # items without timestamps: nothing is older, the plain order stays
    assert order(a, {"timestamp": "2023-07-01"})[0] == "old.txt"


def test_an_index_only_arm_reads_no_source_and_a_scanning_arm_pays_per_record():
    index_only = Bm25Fielded()
    index_only.retrieve("standing desk", FILES)
    assert index_only.source.snapshot() == dict(calls=0, records=0, bytes=0, out_of_scope=0)
    scan = LiveScan()
    scan.retrieve("standing desk", FILES, meta=META, request={"scope_tags": ["owner:1"]})
    snap = scan.source.snapshot()
    assert snap["calls"] == snap["records"] == len(FILES) and snap["bytes"] > 0 and snap["out_of_scope"] == 1   # one record belongs to owner 2


def test_the_source_charge_follows_the_committed_prices():
    from context_retrieval import mix, score
    assert score.source_usd(dict(calls=0, records=0, bytes=0)) == 0.0
    assert score.source_usd(dict(calls=10, records=10, bytes=1_000_000)) == 10 * mix.SOURCE_CALL_USD + 10 * mix.SOURCE_RECORD_USD + mix.SOURCE_MB_USD
