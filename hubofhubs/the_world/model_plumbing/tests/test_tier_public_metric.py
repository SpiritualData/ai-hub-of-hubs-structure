"""The public metric of the tier chooser: planted arms, the shipped anchors and the shipped numbers; no model call, no network."""
from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric as pm
from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers, tiers

DAY = "2026-11-10"
ROWS = pm.read_metrics()
RATES = {"held": (1.0, 2.0), "cheap": (0.5, 1.0), "dear": (5.0, 10.0), "unpriced": None}
rate = lambda provider, model: RATES.get(model)
ANCHOR = ("p", "held")
HELD_SCORES = dict(automationbench_aa=0.6, omniscience_accuracy=0.5, omniscience_non_hallucination=0.5, terminal_bench_4=0.5, frontiercode_2=0.4, critpt_v2_hard=0.5,
                   terminal_bench_science=0.5, hle_diamond=0.5, aa_briefcase=1500.0, gdpval_aa=1500.0, intelligence_index=50.0)


def arm(model, speed=100.0, effort="high", provider="p", checked="2026-11-10", is_default="yes", **scores):
    return dict(provider=provider, model=model, effort=effort, is_default=is_default, output_speed_tps=speed, checked_on=checked, **dict(HELD_SCORES, **scores))


def pick(tier, arms, **kw):
    return pm.choose_public(tier, today=DAY, arms=arms, rows=ROWS, rate=rate, anchor=ANCHOR, **kw)


def test_every_tier_states_weights_that_sum_to_one_and_a_reason():
    for tier in pm.TIERS:
        metric = pm.metric_for(ROWS, tier)
        assert abs(sum(metric["capability"].values()) - 1) < 1e-9, tier
        assert abs(sum(v for k, v in metric["factors"].items() if k in ("cost", "speed", "capability")) - 1) < 1e-9, tier
    assert all(r["reason"].strip() for r in ROWS)
    assert not [r for r in ROWS if r["part"] == "minimum"]                  # no hand-set minimum: each one is anchored to the held default


def test_the_bonus_grows_by_tier_and_stays_small_and_best_has_no_cost_or_speed():
    bonus = [pm.metric_for(ROWS, t)["factors"]["bonus"] for t in ("fast", "balanced", "quality")]
    assert bonus == sorted(bonus) and bonus[0] < bonus[-1] and max(bonus) <= 0.6
    assert set(pm.metric_for(ROWS, "best")["factors"]) == {"capability"}


def test_the_anchors_recorded_in_the_metric_file_are_the_held_defaults():
    held = tiers.default_arms()[0]
    recorded = {(r["tier"], r["role"]): r["measure"] for r in ROWS if r["part"] == "anchor"}
    for tier in ("fast", "balanced", "quality"):
        assert recorded[(tier, "")] == "/".join(held[tier]), tier
    assert recorded[("fast", "science")] == "/".join(held["fast"]) and all("2026-11-10" in r["reason"] for r in ROWS if r["part"] == "anchor")


def test_the_held_default_clears_its_own_anchored_minimums():
    for tier in ("fast", "balanced", "quality"):
        got = pick(tier, [arm("held")])
        assert got["arm"] == ANCHOR and got["ranking"][0]["model"] == "held" and got["minimums"]


def test_a_stronger_dearer_arm_does_not_displace_the_held_default():
    strong = arm("dear", frontiercode_2=0.99, terminal_bench_4=0.99, automationbench_aa=0.99, hle_diamond=0.99, intelligence_index=70.0, gdpval_aa=1900.0)
    for tier in ("fast", "balanced", "quality"):
        got = pick(tier, [strong, arm("held")])
        assert got["arm"] == ANCHOR and [s["model"] for s in got["ranking"]] == ["held", "dear"], tier


def test_a_cheaper_arm_that_clears_the_minimums_displaces_the_held_default():
    for tier in ("fast", "balanced", "quality"):
        assert pick(tier, [arm("held"), arm("cheap", terminal_bench_4=0.49)])["arm"] == ("p", "cheap"), tier    # within the 5 percent tolerance


def test_a_cheaper_arm_under_an_anchored_minimum_cannot_win():
    got = pick("balanced", [arm("held"), arm("cheap", terminal_bench_4=0.40)])
    assert got["arm"] == ANCHOR and any("below the minimum" in e["why"] and e["model"] == "cheap" for e in got["excluded"])


def test_a_missing_anchor_number_drops_that_minimum_and_is_listed():
    held = arm("held")
    del held["gdpval_aa"]
    got = pick("balanced", [held, arm("cheap", gdpval_aa=1.0)])
    assert got["dropped"] == ["gdpval_aa"] and "gdpval_aa" not in got["minimums"] and got["arm"] == ("p", "cheap")      # a cheaper arm clears without it


def test_a_tier_with_no_anchor_row_ranks_nothing_and_best_needs_none():
    assert pm.choose_public("balanced", today=DAY, arms=[arm("cheap")], rows=ROWS, rate=rate, anchor=ANCHOR) is None
    assert pm.choose_public("balanced", today=DAY, arms=[arm("held")], rows=ROWS, rate=rate) is None
    assert pm.choose_public("best", today=DAY, arms=[arm("cheap", intelligence_index=51.0)], rows=ROWS, rate=rate)["arm"] == ("p", "cheap")


def test_the_anchor_counts_even_when_this_install_cannot_call_its_provider():
    arms = [arm("held", provider="a"), arm("cheap", provider="b")]
    got = pm.choose_public("balanced", today=DAY, arms=arms, rows=ROWS, rate=rate, anchor=("a", "held"), available=["b"])
    assert got["arm"] == ("b", "cheap") and got["anchor"]["arm"] == ("a", "held")
    assert pm.choose_public("balanced", today=DAY, arms=arms, rows=ROWS, rate=rate, anchor=("a", "held"), available=[]) is None


def test_best_ignores_cost_and_speed():
    got = pm.choose_public("best", today=DAY, arms=[arm("cheap", intelligence_index=50.0), arm("dear", speed=1.0, intelligence_index=51.0)], rows=ROWS, rate=rate)
    assert got["arm"] == ("p", "dear")


def test_a_missing_number_an_unpriced_arm_or_a_missing_speed_makes_an_arm_ineligible():
    gap = arm("cheap")
    del gap["omniscience_non_hallucination"]
    got = pm.rank([gap, arm("held"), arm("unpriced"), arm("dear", speed=0)], pm.metric_for(ROWS, "balanced"), DAY, rate=rate, anchor=arm("held"))
    assert [s["model"] for s in got["ranking"]] == ["held"]
    assert sorted(e["why"] for e in got["excluded"]) == ["no number for list price", "no number for omniscience_non_hallucination", "no number for output_speed_tps"]


def test_a_stale_row_is_not_used_and_a_stale_anchor_anchors_nothing():
    assert pick("balanced", [arm("held", checked="2026-01-01"), arm("cheap")]) is None


def test_an_effort_the_caller_does_not_apply_is_not_eligible_until_the_caller_applies_it():
    other = arm("cheap", effort="low", is_default="")
    got = pick("balanced", [arm("held"), other])
    assert got["arm"] == ANCHOR and any(e["why"] == "effort not applied by the caller" for e in got["excluded"])
    assert pick("balanced", [arm("held"), other], effort_providers=["p"])["arm"] == ("p", "cheap")


def test_a_tier_of_proxy_evaluations_says_so_and_still_selects():
    assert pm.direct_share(pm.metric_for(ROWS, "fast")) == 0
    got = pick("fast", [arm("held")])
    assert got["evidence"] == "proxy" and got["reason"].startswith("proxy evidence")
    assert pick("balanced", [arm("held")])["evidence"] == "direct"


def test_a_role_variant_replaces_the_capability_weights_and_keeps_the_factors():
    base, science = pm.metric_for(ROWS, "fast"), pm.metric_for(ROWS, "fast", "science")
    assert science["role"] == "science" and set(science["capability"]) != set(base["capability"]) and science["factors"] == base["factors"]
    assert pm.metric_for(ROWS, "balanced", "science")["role"] == ""        # no variant for the tier: the tier's own metric


def test_choose_never_consults_the_hubs_own_measurements(tmp_path):
    import shutil
    for name in ("tier_arms.csv", "tier_prices.csv", "tier_credits.csv", "tier_public_scores.csv"):
        shutil.copy(tiers.registry.DATA / name, tmp_path / name)
    head = "tier,provider,model,cases,passed,tokens_in,tokens_out,source,measured_on\n"
    (tmp_path / "tier_measurements.csv").write_text(head)
    without = tiers.choose(tmp_path, today=DAY)["balanced"]["arm"]
    other = ("anthropic", "claude-haiku-5-5")
    assert without != other
    (tmp_path / "tier_measurements.csv").write_text(
        head + f"balanced,{without[0]},{without[1]},500,1,1000000,200000,t,2026-11-10\nbalanced,{other[0]},{other[1]},500,500,1000000,200000,t,2026-11-10\n")
    assert tiers.choose(tmp_path, today=DAY)["balanced"]["arm"] == without        # 500 shared cases change nothing: public evaluations decide the model


def test_the_shipped_choice_has_four_tiers_each_with_a_breakdown_a_stage_and_an_evidence_mark():
    got = tiers.choose(today=DAY)
    defaults = {(r["provider"], r["model"], r["effort"]) for r in tiers.registry.read("tier_public_scores.csv") if r["is_default"] == "yes"}
    for tier in pm.TIERS:
        one = got[tier]
        assert one["stage"] == "public" and one["evidence"] in ("proxy", "direct") and one["scored"] and (*one["arm"], one["effort"]) in defaults
        assert {"capability", "score"} <= set(one["scored"][0])
    assert got["fast"]["evidence"] == "proxy" and got["cheap"] is got["fast"]


def test_on_the_shipped_data_the_held_defaults_stay_unless_a_cheaper_or_faster_arm_clears():
    held = tiers.default_arms()[0]
    for available in (None, ["anthropic"]):
        got = tiers.choose(today=DAY, available=available)
        for tier in ("fast", "balanced", "quality"):
            top = got[tier]["scored"][0]
            assert got[tier]["arm"] == held[tier] or top["cost_factor"] >= 1.0 or top["speed_factor"] >= 1.0       # a move is a cheaper or faster arm
        assert got["fast"]["dropped"] == [] and all(s["capability"] > 0 for t in ("fast", "balanced", "quality") for s in got[t]["scored"])


def test_an_install_with_one_provider_only_gets_that_providers_arms():
    got = tiers.choose(today=DAY, available=["anthropic"])
    assert all(got[t]["arm"][0] == "anthropic" for t in pm.TIERS)


def test_science_reads_as_fast_and_the_four_tiers_are_the_hubs_own():
    assert role_tiers.normalise("science") == "fast" and tuple(pm.TIERS) == role_tiers.TIERS
