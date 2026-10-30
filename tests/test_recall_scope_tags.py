"""The scope-tag fence: an item scoped to one grouping never answers a turn scoped to another; the kinds are the consumer's."""
from hubofhubs.recall.scope_tags import as_tag_list, scope_tags_allow, scope_tags_from_keys, union_scope_tags


def test_tags_normalise_to_a_deduped_list_of_strings():
    assert as_tag_list(None) == [] and as_tag_list("") == [] and as_tag_list("a:1") == ["a:1"]
    assert as_tag_list(["a:1", "", "a:1", "b:2"]) == ["a:1", "b:2"]
    assert as_tag_list(5) == []


def test_an_untagged_item_or_an_unscoped_turn_hides_nothing():
    assert scope_tags_allow(None, ["p:1"]) and scope_tags_allow(["p:1"], None) and scope_tags_allow([], [])


def test_a_tagged_item_is_visible_only_to_an_intersecting_turn():
    assert scope_tags_allow(["p:1", "p:2"], ["p:2"])
    assert not scope_tags_allow(["p:1"], ["p:2"])


def test_the_kinds_to_fence_are_named_by_the_consumer():
    keys = ["conv:a", "project:x", "global", "project:x", "team:t"]
    assert scope_tags_from_keys(keys, ("project",)) == ["project:x"]
    assert scope_tags_from_keys(keys, ("project", "team")) == ["project:x", "team:t"]
    assert scope_tags_from_keys(keys, ()) == []


def test_union_keeps_first_seen_order_and_ignores_malformed_sources():
    assert union_scope_tags(["a:1", "b:2"], None, "b:2", ["c:3"], 7) == ["a:1", "b:2", "c:3"]
