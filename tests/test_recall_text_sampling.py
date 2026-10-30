"""Text sampling and date bounds: pure helpers the recall code shares. Offline, standard library only."""
from datetime import datetime, timezone

from hubofhubs.recall.date_bounds import parse_date_bound, timestamp_in_range
from hubofhubs.recall.text_sampling import compute_idf, extract_terms, keywords_from_text, select_representatives


def test_keywords_drop_stopwords_and_short_tokens():
    assert keywords_from_text("The plan for the Launch of 2 big ideas") == ["plan", "launch", "big", "ideas"]


def test_extract_terms_drops_stopwords_and_short_parts():
    # The separator pattern needs a separator run followed by a space (", " or ".  "), as it always has.
    assert extract_terms("the, billing, ok, invoice") == {"billing", "invoice"}
    assert extract_terms("alpha, beta", stopwords={"alpha"}) == {"beta"}


def test_idf_rewards_rare_terms_and_floors_absent_ones_at_one():
    idf = compute_idf([{"common", "rare"}, {"common"}, {"common"}])
    assert idf["rare"] > idf["common"] >= 1.0


def test_representatives_prefer_items_that_share_their_group_terms_and_stay_rare_overall():
    items = ["billing/a", "billing/b", "billing/c", "billing/d", "notes/x"]
    terms = {"billing/a": {"invoice", "tax"}, "billing/b": {"invoice", "tax"}, "billing/c": {"invoice", "tax"},
             "billing/d": {"zebra"}, "notes/x": {"zebra"}}
    picked = select_representatives(items, terms.get, samples_per_group=2, get_group=lambda i: i.split("/")[0])
    assert picked[:2] != ["billing/d"] and "billing/d" not in picked[:2] and "notes/x" in picked
    assert select_representatives([], terms.get) == []


def test_a_bare_end_date_includes_the_whole_day_and_garbage_is_an_open_bound():
    start = parse_date_bound("2026-07-09", end_of_day=False)
    end = parse_date_bound("2026-07-09", end_of_day=True)
    assert start == datetime(2026, 7, 9, tzinfo=timezone.utc).timestamp()
    assert end - start == 24 * 3600 - 1
    assert parse_date_bound("not a date", end_of_day=False) is None and parse_date_bound(None, end_of_day=True) is None


def test_timestamp_in_range_treats_a_missing_bound_as_open():
    assert timestamp_in_range(5.0, 1.0, 10.0) and not timestamp_in_range(0.0, 1.0, None) and timestamp_in_range(99.0, None, None)
