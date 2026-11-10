"""The public stage of the tier chooser: planted arms, the shipped weights and the shipped numbers; no model call, no network."""
from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric as pm
from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers, tiers

DAY = "2026-11-10"
ROWS = pm.read_metrics()


def arm(model, cost, time, effort="high", provider="p", checked="2026-11-10", is_default="yes", **scores):
    base = {m: 0.5 for m in ("automationbench_aa", "omniscience_accuracy", "omniscience_non_hallucination", "terminal_bench_4", "frontiercode_2",
                             "critpt_v2_hard", "terminal_bench_science", "hle_diamond")}
    base.update(aa_briefcase=1500.0, gdpval_aa=1500.0, intelligence_index=50.0)
    base.update(scores)
    return dict(provider=provider, model=model, effort=effort, is_default=is_default, cost_per_task_usd=cost, time_per_task_s=time, checked_on=checked, **base)


def test_every_tier_states_weights_that_sum_to_one_and_a_reason():
    for tier in pm.TIERS:
        metric = pm.metric_for(ROWS, tier)
        assert abs(sum(metric["capability"].values()) - 1) < 1e-9 and abs(sum(metric["factors"].values()) - 1) < 1e-9, tier
    assert all(r["reason"].strip() for r in ROWS)


def test_best_has_capability_only_and_the_others_weigh_cost_and_speed_by_use():
    assert set(pm.metric_for(ROWS, "best")["factors"]) == {"capability"}
    f = {t: pm.metric_for(ROWS, t)["factors"] for t in ("fast", "balanced", "quality")}
    assert f["fast"]["cost"] + f["fast"]["speed"] > f["fast"]["capability"]            # speed and cost weigh most for fast
    assert f["quality"]["capability"] > 0.8 and f["quality"]["cost"] > 0 and f["quality"]["speed"] > 0    # capability dominates, the others still count
    assert f["balanced"]["cost"] > f["quality"]["cost"]


def test_cost_and_speed_decide_among_equal_capability_but_never_for_best():
    cheap, dear = arm("cheap", 1, 100), arm("dear", 10, 1000)
    assert pm.choose_public("fast", today=DAY, arms=[dear, cheap], rows=ROWS)["arm"] == ("p", "cheap")
    assert pm.choose_public("best", today=DAY, arms=[cheap, arm("strong", 99, 9999, intelligence_index=51.0)], rows=ROWS)["arm"] == ("p", "strong")


def test_a_missing_number_makes_an_arm_ineligible_and_nothing_is_imputed():
    gap = arm("gap", 0.1, 10)
    del gap["gdpval_aa"]
    got = pm.rank("balanced", [gap, arm("full", 1, 100)], pm.metric_for(ROWS, "balanced"), DAY)
    assert [s["model"] for s in got["ranking"]] == ["full"] and "no number for gdpval_aa" in got["excluded"][0]["why"]


def test_a_zero_score_is_a_number_and_a_zero_cost_is_not():
    zero = arm("zero", 1, 10, critpt_v2_hard=0.0)
    assert pm.rank("quality", [zero], pm.metric_for(ROWS, "quality"), DAY)["ranking"]
    free = arm("free", 0, 10)
    assert pm.rank("fast", [free], pm.metric_for(ROWS, "fast"), DAY)["ranking"] == []


def test_the_fast_accuracy_floor_stops_a_cheap_inaccurate_arm():
    weak = arm("weak", 0.01, 5, automationbench_aa=0.1)
    got = pm.rank("fast", [weak, arm("sound", 1, 100)], pm.metric_for(ROWS, "fast"), DAY)
    assert [s["model"] for s in got["ranking"]] == ["sound"] and "below the floor" in got["excluded"][0]["why"]


def test_a_stale_row_is_not_used():
    old = arm("old", 1, 10, checked="2026-01-01")
    assert pm.choose_public("fast", today=DAY, arms=[old], rows=ROWS) is None


def test_a_provider_that_is_not_available_is_not_chosen():
    arms = [arm("one", 1, 10, provider="a"), arm("two", 5, 50, provider="b")]
    assert pm.choose_public("fast", today=DAY, arms=arms, available=["b"], rows=ROWS)["arm"] == ("b", "two")
    assert pm.choose_public("fast", today=DAY, arms=arms, available=[], rows=ROWS) is None


def test_a_role_variant_replaces_only_the_capability_weights():
    base, science = pm.metric_for(ROWS, "fast"), pm.metric_for(ROWS, "fast", "science")
    assert science["role"] == "science" and set(science["capability"]) != set(base["capability"])
    assert science["factors"] == base["factors"] and science["floors"] == base["floors"]
    assert pm.metric_for(ROWS, "balanced", "science")["role"] == ""        # no variant for the tier: the tier's own metric


def test_an_own_measurement_overrides_only_with_enough_cases(tmp_path):
    import shutil
    for name in ("tier_arms.csv", "tier_prices.csv", "tier_credits.csv", "tier_public_scores.csv"):
        shutil.copy(tiers.registry.DATA / name, tmp_path / name)
    public = tiers.choose(tmp_path, today=DAY)["balanced"]["arm"]
    other = ("anthropic", "claude-sonnet-5-5")
    assert public != other
    head = "tier,provider,model,cases,passed,tokens_in,tokens_out,source,measured_on\n"
    def rows(cases):
        return (head + f"balanced,{public[0]},{public[1]},{cases},{cases // 2},1000000,200000,t,2026-11-10\n"
                + f"balanced,{other[0]},{other[1]},{cases},{cases},1000000,200000,t,2026-11-10\n")
    (tmp_path / "tier_measurements.csv").write_text(rows(30))
    assert tiers.choose(tmp_path, today=DAY)["balanced"]["arm"] == public               # 30 cases: the public default stands
    (tmp_path / "tier_measurements.csv").write_text(rows(100))
    got = tiers.choose(tmp_path, today=DAY)["balanced"]
    assert got["arm"] == other and got["stage"] == "own"                               # 100 cases: the measurement decides


def test_the_shipped_choice_has_four_tiers_and_fast_only_records_its_proxy_ranking():
    got = tiers.choose(today=DAY)
    for tier in ("balanced", "best"):
        one = got[tier]
        assert one["arm"] and one["stage"] == "public" and one["scored"] and {"capability", "score"} <= set(one["scored"][0])
    quality = got["quality"]                                                # a dearer public winner is proposed, not selected
    assert quality["stage"] == "held" and quality["arm"] == tiers.default_arms()[0]["quality"] and quality["proposed"]["arm"] != quality["arm"]
    fast = got["fast"]
    assert fast["stage"] == "held" and fast["arm"] == tiers.default_arms()[0]["fast"] and "no public evaluation fits" in fast["reason"]
    assert fast["scored"] and "score" in fast["scored"][0]                      # the proxy ranking is still returned
    assert got["cheap"] is got["fast"]


def test_a_tier_with_only_proxy_evidence_does_not_select():
    metric = pm.metric_for(ROWS, "fast")
    assert pm.direct_share(metric) == 0 and not pm.choose_public("fast", today=DAY, arms=[arm("a", 1, 10)], rows=ROWS)["selects"]
    for tier in ("balanced", "quality", "best"):
        assert pm.choose_public(tier, today=DAY, arms=[arm("a", 1, 10)], rows=ROWS)["selects"]


def test_an_effort_the_caller_does_not_apply_is_not_eligible_until_the_caller_applies_it():
    other = arm("a", 0.1, 5, effort="low", is_default="")
    default = arm("a", 1, 50, effort="medium")
    got = pm.choose_public("quality", today=DAY, arms=[other, default], rows=ROWS)
    assert got["effort"] == "medium" and any(e["why"] == "effort not applied by the caller" for e in got["excluded"])
    applied = pm.choose_public("quality", today=DAY, arms=[other, default], rows=ROWS, effort_providers=["p"])
    assert {s["effort"] for s in applied["ranking"]} == {"low", "medium"}


def test_every_shipped_choice_is_at_the_efforts_documented_default():
    got = tiers.choose(today=DAY)
    defaults = {(r["provider"], r["model"], r["effort"]) for r in tiers.registry.read("tier_public_scores.csv") if r["is_default"] == "yes"}
    for tier in ("balanced", "best"):
        assert (*got[tier]["arm"], got[tier]["effort"]) in defaults
    assert (*got["quality"]["proposed"]["arm"], got["quality"]["proposed"]["effort"]) in defaults
    assert all(r["default_source"].startswith("https://") for r in tiers.registry.read("tier_public_scores.csv") if r["is_default"] == "yes")


def test_science_reads_as_fast_and_the_four_tiers_are_the_hubs_own():
    assert role_tiers.normalise("science") == "fast" and tuple(pm.TIERS) == role_tiers.TIERS


def planted(tmp_path, winner_price, cases=0, tier="balanced"):
    """A folder with a held default and a public winner of the given list price; ``cases`` of own measurement for both (0: none)."""
    import csv
    header = next(csv.reader((tiers.registry.DATA / "tier_public_scores.csv").open()))
    rows = [arm("held", 5, 50, effort="medium", intelligence_index=40.0, automationbench_aa=0.3, terminal_bench_4=0.3, frontiercode_2=0.3, gdpval_aa=1200.0),
            arm("winner", 1, 10, effort="medium", intelligence_index=60.0)]
    with (tmp_path / "tier_public_scores.csv").open("w", newline="") as handle:
        out = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        out.writeheader()
        for r in rows:
            out.writerow(dict({k: "" for k in header}, source="artificial_analysis", **{k: v for k, v in r.items() if k in header}))
    (tmp_path / "tier_arms.csv").write_text(f"tier,provider,model,role\n{tier},p,held,default\n{tier},p,winner,candidate\n")
    (tmp_path / "tier_prices.csv").write_text("provider,model,input_per_mtok,output_per_mtok,currency,from_prompt_tokens,valid_from,valid_until,source_url,checked_on\n"
                                              "p,held,1,5,USD,,,,https://x.example,2026-11-10\n" f"p,winner,{winner_price},{winner_price},USD,,,,https://x.example,2026-11-10\n")
    (tmp_path / "tier_credits.csv").write_text("provider,balance,allowance,credit_value,currency,period,source_url,checked_on,note\n")
    head = "tier,provider,model,cases,passed,tokens_in,tokens_out,source,measured_on\n"
    body = f"{tier},p,held,{cases},{cases // 10},1000000,200000,t,2026-11-10\n{tier},p,winner,{cases},{cases},1000000,200000,t,2026-11-10\n" if cases else ""
    (tmp_path / "tier_measurements.csv").write_text(head + body)
    return tmp_path


def test_a_cheaper_public_winner_switches_without_more_evidence(tmp_path):
    got = tiers.choose(planted(tmp_path, 0.5), today=DAY)["balanced"]
    assert got["arm"] == ("p", "winner") and got["stage"] == "public" and "proposed" not in got


def test_a_dearer_public_winner_is_proposed_and_not_selected(tmp_path):
    got = tiers.choose(planted(tmp_path, 10), today=DAY)["balanced"]
    assert got["arm"] == ("p", "held") and got["stage"] == "held" and got["proposed"]["arm"] == ("p", "winner") and got["proposed"]["score"] > 0
    assert "costs more than the held default" in got["reason"] and "needs own measurement to switch" in got["reason"]
    assert got["scored"]                                                    # the public ranking is still returned


def test_a_dearer_public_winner_switches_when_the_own_cases_confirm_it(tmp_path):
    got = tiers.choose(planted(tmp_path, 10, cases=100), today=DAY)["balanced"]
    assert got["arm"] == ("p", "winner") and got["stage"] == "own"
    few = tiers.choose(planted(tmp_path, 10, cases=30), today=DAY)["balanced"]
    assert few["arm"] == ("p", "held") and few["proposed"]                  # too few shared cases: the held default stays


def test_best_is_exempt_from_the_cost_guard(tmp_path):
    got = tiers.choose(planted(tmp_path, 10, tier="best"), today=DAY)["best"]
    assert got["arm"] == ("p", "winner") and got["stage"] == "public" and "proposed" not in got
