"""Offline tests for the specificity signal (hubofhubs/critique/specificity.py).

The failure being guarded: a query about one specific subject must not be led by, or answered from, a sibling that only shares
the category. Specificity is measured as neighborhood-IDF: the shared category term is discounted, the rare distinguishing
terms carry the referent. Fully offline, no model, no network.
"""
from __future__ import annotations

from hubofhubs.critique import specificity as sp


# ---------------------------------------------------------------------------
# Unit: the scoring model
# ---------------------------------------------------------------------------

def test_shared_category_term_is_discounted_and_rare_term_carries_specificity():
    # Neighborhood of three "evaluation" docs; only one is about "result prediction".
    cands = [
        "result prediction evaluation truth score methodology",  # the real subject
        "atom evaluation pipeline concept framework",            # sibling A
        "habit evaluation streak scoring",                       # sibling B
    ]
    results = sp.score_candidates("what is next for result prediction evaluation", cands)

    real, sib_a, sib_b = results
    # The on-subject doc scores high and names the distinguishing terms it covered.
    assert real.is_specific and real.score > 0.7
    assert "result" in real.matched or "prediction" in real.matched
    # The siblings share only the category ("evaluation") and miss the distinguishing terms.
    assert not sib_a.is_specific and not sib_b.is_specific
    assert "result" in sib_a.missing or "prediction" in sib_a.missing
    # "evaluation" is common to the whole neighborhood, so it must NOT be treated as distinguishing.
    weights = sp.discriminating_weights([sp.tokenize(c) for c in cands])
    assert weights["evaluation"] < weights["result"]
    assert weights["evaluation"] < weights["prediction"]


def test_neutral_when_no_discriminating_structure():
    # Every candidate shares the same terms: nothing to distinguish on -> neutral, never penalized.
    cands = ["quarterly report status", "quarterly report status", "quarterly report status"]
    results = sp.score_candidates("quarterly report status", cands)
    for r in results:
        assert not r.informative
        assert r.score == 1.0
        assert sp.rerank_factor(r) == 1.0  # neutral factor: ranking unchanged vs no-specificity


def test_rerank_factor_demotes_but_never_zeroes():
    weak = sp.SpecificityResult(score=0.0, informative=True)
    strong = sp.SpecificityResult(score=1.0, informative=True)
    assert sp.rerank_factor(weak) == 0.3        # floored, not zeroed (never-worse)
    assert sp.rerank_factor(strong) == 1.0
    assert sp.rerank_factor(weak) < sp.rerank_factor(strong)


def test_empty_query_is_neutral():
    results = sp.score_candidates("", ["anything here", "and here"])
    assert all(not r.informative and r.score == 1.0 for r in results)
