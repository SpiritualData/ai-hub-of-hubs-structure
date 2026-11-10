"""The role tier table: four tier names, classification always fast, a person's tier wins where allowed, followers resolve, best only for the structure watch or a person's explicit tier."""
import pytest

from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers as policy

TABLE = policy.read_table()


def test_every_row_has_a_known_tier_or_names_another_role_and_an_evidence_mark():
    for role, row in TABLE.items():
        assert row["tier"] in policy.TIERS or row["tier"] in TABLE, role
        assert row["evidence"].startswith(("measured", "owner's policy, unmeasured")), role


def test_classification_roles_are_fast_whatever_a_person_asks():
    for role, row in TABLE.items():
        if row["kind"] == "classify":
            assert policy.tier_for(role, "best") == "fast" and row["person_may_set"] == "no", role


def test_the_default_for_deep_work_is_balanced_and_a_persons_tier_wins():
    assert policy.tier_for("main_session") == "balanced"
    assert policy.tier_for("main_session", "fast") == "fast"
    assert policy.tier_for("main_session", "strong") == "quality"
    assert policy.tier_for("sub_agent", "best") == "best" and policy.tier_for("after_check_resume") == "balanced"
    assert policy.tier_for("web_search", "best") == "fast"


def test_any_response_a_person_reads_is_at_least_balanced():
    order = {t: i for i, t in enumerate(policy.TIERS)}
    for role, row in TABLE.items():
        if row["kind"] == "write":
            assert order[policy.tier_for(role)] >= order["balanced"], role


def test_no_role_but_the_structure_watch_resolves_to_best_unless_the_person_set_it():
    assert [role for role in TABLE if policy.tier_for(role) == "best"] == [policy.BEST_ROLE]
    assert TABLE[policy.BEST_ROLE]["person_may_set"] == "no"
    assert policy.tier_for("main_session", "best") == "best" and policy.tier_for("web_search", "best") == "fast"


def test_strong_is_an_alias_of_quality_in_one_place():
    assert policy.normalise("Strong") == "quality" and policy.normalise("cheap") == "fast" and policy.normalise("mid") == "balanced"
    assert policy.chooser_tier("quality") == "strong" and policy.chooser_tier("best") == "strong"
    assert policy.resolution_note("best") and not policy.resolution_note("quality")


def test_an_unknown_role_fails_loudly_and_a_loop_is_refused():
    with pytest.raises(KeyError):
        policy.tier_for("request_clasification")
    with pytest.raises(ValueError):
        policy.tier_for("a", table={"a": {"tier": "b", "person_may_set": "no"}, "b": {"tier": "a", "person_may_set": "no"}})


def test_no_row_names_a_model():
    for row in TABLE.values():
        assert not any(name in " ".join(row.values()).lower() for name in ("haiku", "sonnet", "opus", "gemini", "gpt"))
