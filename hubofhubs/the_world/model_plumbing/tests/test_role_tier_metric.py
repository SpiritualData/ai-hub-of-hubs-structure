"""The role-tier metric: the rule on small planted inputs, the rule file's own consistency, and the table on disk equal to the table recomputed from the registry."""
import csv
import math

from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers as rt

DAY = "2026-11-11"
RULES = rt.read_rules()
KINDS = ("classify", "gather", "orchestrate", "work", "review", "write", "structure")


def planted(**kw):
    """A tier's public row: every evaluation of every kind at one level, overridden by keyword."""
    base = {m: 0.5 for m in {r["key"] for r in RULES if r["part"] == "evaluation"}}
    base.update({m: 1500.0 for m in ("aa_briefcase", "gdpval_aa")})
    base.update(kw, checked_on="2026-11-10")
    return base


def level(value, elo=1500.0):
    return {m: (elo if m in ("aa_briefcase", "gdpval_aa") else value) for m in {r["key"] for r in RULES if r["part"] == "evaluation"}}


def walk(kind="work", frequency="turn", stakes="turn", fast=0.3, balanced=0.5, quality=0.5, prices=None, day=DAY, role=""):
    arms = {"fast": planted(**level(fast)), "balanced": planted(**level(balanced)), "quality": planted(**level(quality))}
    return rt.climb(RULES, kind, role, frequency, stakes, arms, prices or {"fast": 1.0, "balanced": 2.0, "quality": 4.0}, day)


def test_the_rule_file_is_consistent_and_every_part_has_a_reason():
    assert all(r["reason"].strip() for r in RULES)
    for kind in KINDS:
        evals = rt.evaluations_for(RULES, kind)
        assert abs(sum(w for w, _ in evals.values()) - 1) < 1e-9 and {f for _, f in evals.values()} <= {"direct", "proxy"}, kind
    assert {r["key"] for r in RULES if r["part"] == "frequency"} == {"many", "turn", "rare"}
    assert {r["key"] for r in RULES if r["part"] == "stakes"} == {"call", "turn", "structure"}
    assert rt.ladder_for(RULES) == ("fast", "balanced", "quality")


def test_every_role_has_a_kind_a_frequency_and_a_stakes_class_the_rule_defines():
    table = rt.read_table()
    freq = {r["key"] for r in RULES if r["part"] == "frequency"}
    stakes = {r["key"] for r in RULES if r["part"] == "stakes"}
    for role, row in table.items():
        assert row["kind"] in KINDS and row["frequency"] in freq and row["stakes"] in stakes, role


def test_the_threshold_grows_with_frequency_and_price_and_shrinks_with_stakes():
    base = rt.threshold(RULES, "turn", "call", 1.0, 2.0)[0]
    assert math.isclose(base, 0.10)
    assert rt.threshold(RULES, "many", "call", 1.0, 2.0)[0] > base > rt.threshold(RULES, "rare", "call", 1.0, 2.0)[0]
    assert rt.threshold(RULES, "turn", "call", 1.0, 8.0)[0] > base
    assert rt.threshold(RULES, "turn", "turn", 1.0, 2.0)[0] < base and rt.threshold(RULES, "turn", "structure", 1.0, 2.0)[0] < rt.threshold(RULES, "turn", "turn", 1.0, 2.0)[0]
    assert rt.threshold(RULES, "turn", "call", 1.0, 1.5)[1] == 1.0         # a step under double the price asks for the base gain once


def test_a_role_stays_on_the_lowest_tier_unless_the_next_tier_up_shows_the_gain():
    assert walk(fast=0.5, balanced=0.5, quality=0.5)["tier"] == "fast"                       # no gain
    assert walk(fast=0.2, balanced=0.8, quality=0.8)["tier"] == "balanced"                   # big gain once, none after
    assert walk(fast=0.2, balanced=0.6, quality=1.0, stakes="structure", frequency="rare")["tier"] == "quality"


def test_the_same_gain_is_enough_for_an_infrequent_high_stakes_call_but_not_for_a_frequent_cheap_one():
    # the gain here is below the many-calls threshold and above the rare, structure one
    assert walk(fast=0.5, balanced=0.62, quality=0.62, frequency="many", stakes="call")["tier"] == "fast"
    assert walk(fast=0.5, balanced=0.62, quality=0.62, frequency="rare", stakes="structure")["tier"] == "balanced"


def test_a_dearer_next_tier_asks_for_more():
    cheap = {"fast": 1.0, "balanced": 1.5, "quality": 2.0}
    dear = {"fast": 1.0, "balanced": 20.0, "quality": 40.0}
    assert walk(fast=0.5, balanced=0.6, quality=0.6, prices=cheap)["tier"] == "balanced"      # a gain of a sixth: over 0.05, under 0.22
    assert walk(fast=0.5, balanced=0.6, quality=0.6, prices=dear)["tier"] == "fast"


def test_a_gain_that_is_negative_never_steps_up_and_an_elo_rating_reads_as_a_chance():
    assert walk(fast=0.8, balanced=0.4, quality=0.4, stakes="structure", frequency="rare")["tier"] == "fast"
    low, high = planted(gdpval_aa=1400.0), planted(gdpval_aa=1800.0)
    got = rt.gain({"gdpval_aa": (1.0, "direct")}, low, high)
    assert 0.8 < got["gain"] < 0.85 and got["direct"] == 1.0          # 1400 against 1800: a chance of 0.09 for the lower, so a share of 0.18 against 1


def test_an_evaluation_with_no_number_is_dropped_and_listed_never_guessed():
    low, high = planted(), planted(hle_diamond=0.9)
    low["gdpval_aa"] = None
    got = rt.gain({"gdpval_aa": (0.5, "direct"), "hle_diamond": (0.5, "proxy")}, low, high)
    assert got["dropped"] == ["gdpval_aa"] and list(got["used"]) == ["hle_diamond"] and got["direct"] == 0.0


def test_stale_numbers_are_reported_and_never_used():
    got = walk(fast=0.2, balanced=0.9, quality=0.9, day="2027-01-30")
    assert got["tier"] is None and "days old" in got["unmeasured"]
    row = rt.role_row(dict(role="x", kind="work", frequency="turn", stakes="turn", follows="", person_may_set="no", own_measurement="", reason="r"), RULES,
                      {"fast": planted(**level(0.2)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.9))},
                      {"fast": 1.0, "balanced": 2.0, "quality": 4.0}, "2027-01-30", {"x": "balanced"})
    assert row["tier"] == "balanced" and row["evidence"].startswith("STALE OR MISSING") and "not applied" in row["evidence"]


def test_a_missing_price_or_tier_model_is_reported_not_guessed():
    arms = {"fast": planted(), "balanced": planted()}
    got = rt.climb(RULES, "work", "", "turn", "turn", arms, {"fast": 1.0}, DAY)
    assert got["tier"] is None and "no list price" in got["unmeasured"]
    missing = rt.climb(RULES, "work", "", "turn", "turn", {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9))}, {"fast": 1.0, "balanced": 2.0, "quality": 4.0}, DAY)
    assert missing["tier"] is None and "no model for the quality tier" in missing["unmeasured"]


def test_hard_constraints_apply_after_the_metric_and_the_row_still_shows_the_metric_alone():
    arms = {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.95))}
    prices = {"fast": 1.0, "balanced": 2.0, "quality": 4.0}
    row = lambda role, kind, freq="rare", stakes="structure": rt.role_row(dict(role=role, kind=kind, frequency=freq, stakes=stakes, follows="", person_may_set="no",
                                                                           own_measurement="", reason="r"), RULES, arms, prices, DAY)
    classify = row("c", "classify")
    assert classify["tier"] == "fast" and classify["metric_tier"] != "fast" and "would have picked" in classify["evidence"] and classify["constraint"] == "classify_fast_only"
    write = rt.role_row(dict(role="w", kind="write", frequency="many", stakes="call", follows="", person_may_set="no", own_measurement="", reason="r"), RULES,
                        {"fast": planted(**level(0.5)), "balanced": planted(**level(0.5)), "quality": planted(**level(0.5))}, prices, DAY)
    assert write["metric_tier"] == "fast" and write["tier"] == "balanced" and "person_reads_balanced_min" in write["evidence"]
    watch = row("structure-watch", "structure")
    assert watch["tier"] == "best" and watch["metric_tier"] == "quality"
    assert rt.apply_constraints("quality", []) == "quality"


def test_the_deep_work_default_is_a_constraint_of_main_session_alone_and_a_person_still_wins():
    named = {r["role"] for r in RULES if r["part"] == "constraint" and r["key"] == "deep_work_default_balanced"}
    assert named == {"main_session"}
    assert [n for n, _, _ in rt.constraints_for(RULES, "work", "main_session")] == ["deep_work_default_balanced"]
    assert rt.constraints_for(RULES, "work", "file_editing") == []
    table = rt.read_table()
    assert table["main_session"]["tier"] == "balanced" and rt.tier_for("main_session", "quality", table) == "quality"
    assert table["sub_agent"]["tier"] == "main_session" and rt.tier_for("sub_agent") == "balanced"
    assert "would have picked" in table["main_session"]["evidence"]


def test_a_role_that_follows_another_keeps_its_own_metric_result_and_names_the_role():
    arms = {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.9))}
    row = rt.role_row(dict(role="s", kind="work", frequency="many", stakes="turn", follows="main_session", person_may_set="no", own_measurement="", reason="r"), RULES,
                      arms, {"fast": 1.0, "balanced": 2.0, "quality": 4.0}, DAY)
    assert row["tier"] == "main_session" and row["metric_tier"] == "balanced" and "follows main_session" in row["evidence"]


def test_a_roles_own_evaluation_rows_replace_its_kinds_so_a_role_can_diverge_from_the_ladder():
    mine = RULES + [dict(part="evaluation", kind="", role="special", key="hle_diamond", weight="1.0", fit="direct", value="", reason="r"),
                    dict(part="ladder", kind="", role="special", key="fast", weight="", fit="", value="1", reason="r"),
                    dict(part="ladder", kind="", role="special", key="quality", weight="", fit="", value="2", reason="r")]
    assert rt.evaluations_for(mine, "work", "special") == {"hle_diamond": (1.0, "direct")}
    assert rt.ladder_for(mine, "work", "special") == ("fast", "quality") and rt.ladder_for(mine, "work", "other") == ("fast", "balanced", "quality")


def test_the_table_on_disk_is_the_table_recomputed_from_the_registry_for_its_date():
    with rt.TABLE.open(newline="", encoding="utf-8") as handle:
        on_disk = list(csv.DictReader(handle))
    day = on_disk[0]["computed_on"]
    assert day == DAY and {r["computed_on"] for r in on_disk} == {day}
    again = rt.compute_table(day)
    assert [dict(r) for r in on_disk] == [{k: v for k, v in r.items()} for r in again]    # a refreshed registry fails this until write_table(day) is run again


def test_no_row_of_the_table_says_unmeasured_names_a_model_or_leaves_evidence_empty():
    for role, row in rt.read_table().items():
        text = " ".join(row.values()).lower()
        assert row["evidence"] and "unmeasured" not in text and "owner's policy" not in row["evidence"].lower(), role
        assert row["evidence"].startswith(("direct public", "proxy public", "STALE OR MISSING")), role
        assert not any(name in text for name in ("haiku", "sonnet", "opus", "fable", "gemini", "gpt", "deepseek")), role
