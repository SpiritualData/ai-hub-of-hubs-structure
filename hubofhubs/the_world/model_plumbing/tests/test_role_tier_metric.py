"""The role-tier metric: the rule on small planted inputs, the rule file's own consistency, and the table on disk equal to the table recomputed from the registry."""
import csv

from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers as rt

DAY = "2026-11-11"
RULES = rt.read_rules()
KINDS = ("classify", "gather", "orchestrate", "work", "review", "write", "structure")
PRICES = {"fast": (0.1, 0.5), "balanced": (2.0, 10.0), "quality": (4.0, 20.0)}


def planted(**kw):
    """A tier's public row: every evaluation of every kind at one level, overridden by keyword."""
    base = {m: 0.5 for m in {r["key"] for r in RULES if r["part"] == "evaluation"}}
    base.update({m: 1500.0 for m in ("aa_briefcase", "gdpval_aa")})
    base.update(kw, checked_on="2026-11-10")
    return base


def level(value, elo=1500.0):
    return {m: (elo if m in ("aa_briefcase", "gdpval_aa") else value) for m in {r["key"] for r in RULES if r["part"] == "evaluation"}}


def walk(kind="work", frequency="turn", stakes="turn", fast=0.3, balanced=0.5, quality=0.5, prices=None, day=DAY, role="", tokens=(840.0, 76.0)):
    arms = {"fast": planted(**level(fast)), "balanced": planted(**level(balanced)), "quality": planted(**level(quality))}
    return rt.climb(RULES, kind, role, frequency, stakes, arms, prices or PRICES, day, tokens=tokens)


def test_the_rule_file_is_consistent_and_every_part_has_a_reason():
    assert all(r["reason"].strip() for r in RULES)
    for kind in KINDS:
        evals = rt.evaluations_for(RULES, kind)
        assert abs(sum(w for w, _ in evals.values()) - 1) < 1e-9 and {f for _, f in evals.values()} <= {"direct", "proxy"}, kind
    assert {r["key"] for r in RULES if r["part"] == "frequency"} == {"many", "turn", "rare"}
    assert {r["key"] for r in RULES if r["part"] == "stakes"} == {"call", "turn", "task", "structure"}
    assert {r["key"] for r in RULES if r["part"] == "volume"} == {"small", "medium", "large", "session"}
    assert rt.ladder_for(RULES) == ("fast", "balanced", "quality")
    assert [r["key"] for r in RULES if r["part"] == "revision"] == ["1", "2", "3", "4", "5", "6"]      # the revisions on the owner's instruction are recorded, with his words
    assert any(r["part"] == "assumption" for r in RULES)                                # the dollar values and the cost weight are stated as assumptions


def test_every_role_has_a_kind_and_classes_the_rule_defines_and_a_measured_volume_says_its_basis():
    table = rt.read_table()
    freq = {r["key"] for r in RULES if r["part"] == "frequency"}
    stakes = {r["key"] for r in RULES if r["part"] == "stakes"}
    volumes = {r["key"] for r in RULES if r["part"] == "volume"} | {"measured"}
    for role, row in table.items():
        assert row["kind"] in KINDS and row["frequency"] in freq and row["stakes"] in stakes and row["volume"] in volumes, role
        if row["volume"] == "measured":
            assert row["tokens_in"] and row["tokens_out"] and row["volume_basis"], role


def test_no_constraint_sets_a_deep_work_tier():
    named = {(r["role"], r["kind"]) for r in RULES if r["part"] == "constraint"}
    assert not any(role.startswith("deep_work") or role == "main_session" for role, _ in named)
    assert {r["key"] for r in RULES if r["part"] == "constraint"} == {"classify_fast_only", "person_reads_balanced_min", "best_only_on_request_or_watch", "significant_downstream_effect_quality_min"}


def test_the_required_gain_is_the_larger_of_the_noise_floor_and_the_weighted_cost_over_the_value_of_gain():
    cheap = rt.required_gain(RULES, "turn", "turn", PRICES["fast"], PRICES["balanced"], (840, 76))
    assert cheap["limit"] == 0.10 and cheap["by_cost"] < 0.10                                  # a small call: the noise floor binds
    assert abs(cheap["added_cost"] - 2 * (1.9 * 840 + 9.5 * 76) / 1e6) < 1e-12
    big = rt.required_gain(RULES, "many", "call", PRICES["fast"], PRICES["balanced"], (20000, 3000))
    assert big["limit"] == big["by_cost"] > 1                                                  # many large cheap-value calls: cost binds and no gain can pay
    assert rt.required_gain(RULES, "turn", "structure", PRICES["fast"], PRICES["balanced"], (20000, 3000))["by_cost"] < \
        rt.required_gain(RULES, "turn", "call", PRICES["fast"], PRICES["balanced"], (20000, 3000))["by_cost"]     # the more a mistake is worth, the lower the bar
    assert rt.required_gain(RULES, "many", "turn", PRICES["fast"], PRICES["balanced"], (4000, 500))["by_cost"] > \
        rt.required_gain(RULES, "rare", "turn", PRICES["fast"], PRICES["balanced"], (4000, 500))["by_cost"]       # more calls, more cost


def test_cache_reads_and_writes_are_priced_at_their_multipliers_of_the_input_price():
    price = (2.0, 10.0, 0.1, 1.25)
    assert abs(rt.call_cost(price, (0, 0, 0, 1_000_000)) - 0.2) < 1e-12 and abs(rt.call_cost(price, (0, 0, 1_000_000, 0)) - 2.5) < 1e-12
    assert abs(rt.call_cost((2.0, 10.0), (0, 0, 0, 1_000_000)) - 2.0) < 1e-12 and abs(rt.call_cost(price, (1_000_000, 1_000_000, 0, 0)) - 12.0) < 1e-12
    cached = rt.required_gain(RULES, "turn", "task", PRICES["fast"] + (0.1, 1.25), PRICES["balanced"] + (0.1, 1.25), (0, 0, 0, 1_000_000))
    plain = rt.required_gain(RULES, "turn", "task", PRICES["fast"], PRICES["balanced"], (0, 0, 0, 1_000_000))
    assert abs(cached["added_cost"] * 10 - plain["added_cost"]) < 1e-12                       # the discount is real: a tenth of the uncached cost


def test_no_deep_run_role_depends_on_the_cost_weight_or_the_value_of_a_gain():
    inputs = {i["role"]: i for i in rt.read_inputs()}
    measured = rt.measured_pass_rates()
    ladder = [dict(r) for r in RULES]
    for r in ladder:
        if r["part"] == "stakes":
            r["value"] = str(float(r["value"]) * 100)
        if r["part"] == "rule" and r["key"] == "cost_weight":
            r["value"] = "300"
    for role in (r for r in rt.deep_run_roles(RULES) if not rt.own_evidence_for(RULES, r)):          # a role with its own evidence is tested in test_deep_run_tier_rule.py
        a = rt.role_row(inputs[role], RULES, {}, {}, DAY, measured=measured)["metric_tier"]
        b = rt.role_row(inputs[role], ladder, {}, {}, DAY, measured=measured)["metric_tier"]
        assert a == b == "fast", role


def test_a_role_that_spends_many_tokens_stays_on_the_cheap_tier_that_the_cost_term_works_out_by_itself():
    heavy, light = (3_000_000, 200_000), (840, 76)
    assert walk(fast=0.2, balanced=0.8, quality=0.8, frequency="rare", stakes="task", tokens=heavy)["tier"] == "fast"
    assert walk(fast=0.2, balanced=0.8, quality=0.8, frequency="rare", stakes="task", tokens=light)["tier"] == "balanced"


def test_a_role_stays_on_the_lowest_tier_unless_the_next_tier_up_shows_the_gain():
    assert walk(fast=0.5, balanced=0.5, quality=0.5)["tier"] == "fast"                       # no gain
    assert walk(fast=0.2, balanced=0.8, quality=0.8)["tier"] == "balanced"                   # big gain once, none after
    assert walk(fast=0.2, balanced=0.6, quality=1.0, stakes="structure", frequency="rare")["tier"] == "quality"


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
    row = rt.role_row(dict(role="x", kind="work", frequency="turn", stakes="turn", volume="small", follows="", person_may_set="no", own_measurement="", reason="r"), RULES,
                      {"fast": planted(**level(0.2)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.9))}, PRICES, "2027-01-30", {"x": "balanced"})
    assert row["tier"] == "balanced" and row["evidence"].startswith("STALE OR MISSING") and "not applied" in row["evidence"]


def test_a_missing_price_or_tier_model_is_reported_not_guessed():
    arms = {"fast": planted(), "balanced": planted()}
    got = rt.climb(RULES, "work", "", "turn", "turn", arms, {"fast": (0.1, 0.5)}, DAY)
    assert got["tier"] is None and "no list price" in got["unmeasured"]
    missing = rt.climb(RULES, "work", "", "turn", "turn", {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9))}, PRICES, DAY)
    assert missing["tier"] is None and "no model for the quality tier" in missing["unmeasured"]


def test_hard_constraints_apply_after_the_metric_and_the_row_still_shows_the_metric_alone():
    arms = {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.95))}
    base = dict(frequency="rare", stakes="structure", volume="small", follows="", person_may_set="no", own_measurement="", reason="r")
    classify = rt.role_row(dict(base, role="c", kind="classify"), RULES, arms, PRICES, DAY)
    assert classify["tier"] == "fast" and classify["metric_tier"] != "fast" and "would have picked" in classify["evidence"] and classify["constraint"] == "classify_fast_only"
    write = rt.role_row(dict(base, role="w", kind="write", frequency="many", stakes="call"), RULES,
                        {"fast": planted(**level(0.5)), "balanced": planted(**level(0.5)), "quality": planted(**level(0.5))}, PRICES, DAY)
    assert write["metric_tier"] == "fast" and write["tier"] == "balanced" and "person_reads_balanced_min" in write["evidence"]
    climbing = {"fast": planted(**level(0.1)), "balanced": planted(**level(0.5)), "quality": planted(**level(0.9))}
    watch = rt.role_row(dict(base, role="structure-watch", kind="structure"), RULES, climbing, PRICES, DAY)
    assert watch["tier"] == "best" and watch["metric_tier"] == "quality"
    assert rt.apply_constraints("quality", []) == "quality"


def test_a_role_that_follows_another_keeps_its_own_metric_result_and_names_the_role():
    arms = {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.9))}
    row = rt.role_row(dict(role="s", kind="work", frequency="many", stakes="turn", volume="small", follows="main_session", person_may_set="no", own_measurement="", reason="r"), RULES,
                      arms, PRICES, DAY)
    assert row["tier"] == "main_session" and row["metric_tier"] == "balanced" and "follows main_session" in row["evidence"]


def test_a_measured_volume_is_used_as_given_and_named_in_the_evidence():
    arms = {"fast": planted(**level(0.1)), "balanced": planted(**level(0.9)), "quality": planted(**level(0.9))}
    row = rt.role_row(dict(role="m", kind="work", frequency="turn", stakes="turn", volume="measured", tokens_in="1000", tokens_out="100", volume_basis="a recorded run",
                           follows="", person_may_set="no", own_measurement="", reason="r"), RULES, arms, PRICES, DAY)
    assert "1000 in, 100 out, 0 cache write, 0 cache read (measured: a recorded run)" in row["evidence"]
    assert rt.volume_of(RULES, "session") == (46.0, 14272.0, 99938.0, 1907198.0)          # the measured medians of recorded sessions, cache tokens included
    assert rt.volume_of(RULES, "small") == (840.0, 76.0, 0.0, 0.0)


def test_a_roles_own_evaluation_rows_replace_its_kinds_so_a_role_can_diverge_from_the_ladder():
    mine = RULES + [dict(part="evaluation", kind="", role="special", key="hle_diamond", weight="1.0", fit="direct", value="", reason="r"),
                    dict(part="ladder", kind="", role="special", key="fast", weight="", fit="", value="1", reason="r"),
                    dict(part="ladder", kind="", role="special", key="quality", weight="", fit="", value="2", reason="r")]
    assert rt.evaluations_for(mine, "work", "special") == {"hle_diamond": (1.0, "direct")}
    assert rt.ladder_for(mine, "work", "special") == ("fast", "quality") and rt.ladder_for(mine, "work", "other") == ("fast", "balanced", "quality")


def test_deep_work_takes_its_tier_from_the_task_kind_and_a_person_still_wins():
    table = rt.read_table()
    kinds = rt.task_kinds(table)
    assert set(kinds) == {"gather", "implementation", "structure", "review"} and all(table[r]["person_may_set"] == "yes" for r in kinds.values())
    for kind, role in kinds.items():
        assert rt.tier_for_task(kind, table=table) == rt.tier_for(role, table=table)
    assert rt.tier_for_task("", table=table) == rt.tier_for_task("implementation", table=table) == rt.tier_for("main_session", table=table)     # no known kind: implementation
    assert rt.tier_for_task("unheard-of", table=table) == rt.tier_for_task("implementation", table=table)
    assert rt.tier_for_task("gather", "quality", table) == "quality" and rt.tier_for_task("structure", "fast", table) == "fast" and rt.tier_for("after_check_resume", "best", table) == "best" and rt.tier_for("sub_agent", "best", table) == "fast"     # a sub-agent does not take the main session's tier
    order = {t: i for i, t in enumerate(rt.TIERS)}
    assert order[rt.tier_for_task("gather", table=table)] <= order[rt.tier_for_task("implementation", table=table)] <= order[rt.tier_for_task("structure", table=table)]


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
        assert row["evidence"].startswith(("direct public", "proxy public", "sufficiency rule", "STALE OR MISSING")), role
        assert not any(name in text for name in ("haiku", "sonnet", "opus", "fable", "gemini", "gpt", "deepseek")), role
