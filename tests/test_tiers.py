"""Offline tests of the tier-selection scorer: planted arms, prices and credits, no model call, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import registry, tiers  # noqa: E402

PRICES = [dict(provider="p", model=m, input_per_mtok=i, output_per_mtok=o) for m, i, o in
          (("small", "1", "5"), ("big", "10", "50"), ("tiny", "0.1", "0.5"), ("mid", "3", "15"))]


def arm(model, passed, cases=10, provider="p"):
    return dict(provider=provider, model=model, cases=cases, passed=passed, tokens_in=1_000_000, tokens_out=200_000)


# per tier: the cost-effective arm, a pricey slightly better one, and a near-free arm that fails
TIERS = {"cheap": [arm("small", 9), arm("big", 10), arm("tiny", 0)], "mid": [arm("mid", 9), arm("big", 10), arm("tiny", 0)]}


def test_the_best_passing_work_per_cost_wins_and_records_why():
    got = tiers.pick(TIERS["cheap"], PRICES)
    assert got["arm"] == ("p", "small") and "passing cases per cost" in got["reason"]


def test_a_tie_goes_to_the_cheaper_arm():
    prices = [dict(provider="p", model=m, input_per_mtok="1", output_per_mtok="0") for m in ("a", "b")]
    dear, cheap = arm("a", 10), dict(arm("b", 5), tokens_in=500_000)     # equal passing work per cost, half the money
    for order in ([dear, cheap], [cheap, dear]):
        assert tiers.pick(order, prices)["arm"] == ("p", "b")


def test_floor_never_switches_without_a_measurement():
    got = tiers.pick([arm("small", 9, cases=0), arm("tiny", 0, cases=0)], PRICES, default=("p", "small"))
    assert got["arm"] == ("p", "small") and "kept" in got["reason"]
    challenger_only = tiers.pick([arm("small", 0, cases=0), arm("tiny", 9)], PRICES, default=("p", "small"))
    assert challenger_only["arm"] == ("p", "small")          # the held arm has no measurement to compare against
    assert tiers.pick([arm("tiny", 0, cases=0)], PRICES)["arm"] is None


def test_an_unpriced_arm_is_never_chosen():
    assert tiers.pick([arm("ghost", 10), arm("small", 5)], PRICES)["arm"] == ("p", "small")


def test_a_measured_challenger_replaces_the_held_arm():
    got = tiers.pick([arm("small", 5), arm("tiny", 5)], PRICES, default=("p", "small"))
    assert got["arm"] == ("p", "tiny")


def test_credits_reduce_money_but_are_a_cost_of_their_own_value():
    credits = [dict(provider="p", balance="3", allowance="0", credit_value="0.5")]
    listed, spent, used, effective = tiers.arm_cost(arm("small", 9), PRICES, credits)
    assert (round(listed, 6), round(used, 6), round(spent, 6)) == (2.0, 2.0, 0.0)
    assert round(effective, 6) == 1.0                         # not free: half the face value of the credit counts
    none = tiers.arm_cost(arm("small", 9), PRICES, [])
    assert none[3] == listed and none[1] == listed
    partial = tiers.arm_cost(arm("big", 10), PRICES, [dict(provider="p", balance="5", allowance="3", credit_value="1")])
    assert round(partial[1], 6) == 12.0 and round(partial[3], 6) == 20.0   # value 1: credits cost their face value
    other = tiers.arm_cost(arm("small", 9), PRICES, [dict(provider="elsewhere", balance="99", allowance="", credit_value="0.5")])
    assert other[2] == 0                                      # credits only cover their own provider


def test_credits_can_change_the_winner_through_the_metric():
    near_free_credit = [dict(provider="free", balance="100", allowance="", credit_value="0.01")]
    prices = PRICES + [dict(provider="free", model="big", input_per_mtok="10", output_per_mtok="50")]
    arms = [arm("small", 9), arm("big", 10, provider="free")]
    assert tiers.pick(arms, prices)["arm"] == ("p", "small")
    assert tiers.pick(arms, prices, near_free_credit)["arm"] == ("free", "big")


def test_the_scorer_separates_ideal_from_broken_baselines():
    ideal = tiers.portfolio(tiers.scripted_choices(TIERS, PRICES), TIERS, PRICES)
    expensive = tiers.portfolio(tiers.always_most_expensive(TIERS, PRICES), TIERS, PRICES)
    cheapest = tiers.portfolio(tiers.always_cheapest(TIERS, PRICES), TIERS, PRICES)
    assert tiers.always_most_expensive(TIERS, PRICES) == {"cheap": ("p", "big"), "mid": ("p", "big")}
    assert tiers.always_cheapest(TIERS, PRICES) == {"cheap": ("p", "tiny"), "mid": ("p", "tiny")}
    assert ideal > expensive * 1.5 and ideal > cheapest * 1.5


def test_default_arms_are_data_with_one_cheap_default_and_candidates_not_defaults():
    held, candidates = tiers.default_arms()
    assert held["cheap"] == ("anthropic", "claude-haiku-5-5") and set(held) == {"cheap", "mid", "strong"}
    assert all(p == "anthropic" for p, _ in held.values())
    assert candidates["cheap"] and not any(c in held.values() for c in candidates["cheap"])


def test_price_rows_carry_a_source_and_a_checked_date_when_they_hold_a_number():
    for row in registry.read("tier_prices.csv"):
        if row["input_per_mtok"] or row["output_per_mtok"]:
            assert row["source_url"].startswith("https://") and registry.days_since(row["checked_on"]) is not None


def test_a_blank_credit_value_is_face_value_never_free():
    credits = [dict(provider="p", balance="", allowance="3", credit_value="")]
    listed, spent, used, effective = tiers.arm_cost(arm("small", 9), PRICES, credits)
    assert (round(used, 6), round(spent, 6), round(effective, 6)) == (2.0, 0.0, 2.0) and effective == listed


def test_the_recorded_prices_are_the_official_ones_with_their_tiers_and_dates():
    prices = registry.read("tier_prices.csv")
    assert tiers.rates(prices, "anthropic", "claude-haiku-5-5") == (0.10, 0.50)
    assert tiers.rates(prices, "anthropic", "claude-haiku-5-5", prompt_tokens=100_000) == (0.50, 2.50)
    assert tiers.rates(prices, "anthropic", "claude-sonnet-5-5") == (2.0, 10.0)
    assert tiers.rates(prices, "anthropic", "claude-opus-5-5") == (4.0, 20.0)
    assert tiers.rates(prices, "gemini", "gemini-3.1-flash-lite") == (0.25, 1.50)
    assert tiers.rates(prices, "gemini", "gemini-3.6-flash", day="2026-12-31") == (0.75, 3.75)
    assert tiers.rates(prices, "gemini", "gemini-3.6-flash", day="2027-01-01") == (1.50, 7.50)
    assert tiers.rates(prices, "anthropic", "no-such-model") is None
    assert round(tiers.list_cost(prices, "anthropic", "claude-haiku-5-5", 50_000, 50_000), 6) == 0.03
    assert round(tiers.list_cost(prices, "anthropic", "claude-haiku-5-5", 200_000, 100_000), 6) == 0.35


def test_choose_keeps_each_default_with_no_measurement():
    got = tiers.choose()
    assert {t: r["arm"] for t, r in got.items()} == {"cheap": ("anthropic", "claude-haiku-5-5"), "mid": ("anthropic", "claude-sonnet-5-5"),
                                                      "strong": ("anthropic", "claude-opus-5-5")}
    assert registry.read("tier_credits.csv") == []             # the hub ships the schema only: allowances are the consumer's own


def test_the_hub_holds_no_allowance_and_a_consumer_passes_its_own_credits():
    assert registry.read("tier_credits.csv") == []
    plain = tiers.choose()["cheap"]["scored"]
    own = [dict(provider="anthropic", balance="", allowance="200", credit_value="0.5")]
    assert tiers.credit_of([], "anthropic") == (0.0, 1.0) and tiers.credit_of(own, "anthropic") == (200.0, 0.5)
    assert plain == tiers.choose(credits=[])["cheap"]["scored"]
    measured = {"cheap": [dict(provider="anthropic", model="claude-haiku-5-5", cases=10, passed=9, tokens_in=1_000_000, tokens_out=200_000)]}
    prices = registry.read("tier_prices.csv")
    free = tiers.pick(measured["cheap"], prices, own)["scored"][0]
    paid = tiers.pick(measured["cheap"], prices, [])["scored"][0]
    assert free["credits_used"] > 0 and free["money_spent"] == 0 and paid["credits_used"] == 0 and paid["money_spent"] > 0
    assert free["cost"] < paid["cost"]                          # half-value credits cost half, so the same work is cheaper


def test_choose_scores_measured_arms_with_the_credits_it_is_given(tmp_path):
    import shutil
    for name in ("tier_arms.csv", "tier_prices.csv", "tier_credits.csv", "tier_measurements.csv"):
        shutil.copy(registry.DATA / name, tmp_path / name)
    (tmp_path / "tier_measurements.csv").write_text(
        "tier,provider,model,cases,passed,tokens_in,tokens_out,source,measured_on\n"
        "cheap,anthropic,claude-haiku-5-5,10,9,1000000,200000,test,2026-10-30\n")
    own = [dict(provider="anthropic", balance="", allowance="200", credit_value="")]
    without = tiers.choose(tmp_path)["cheap"]["scored"][0]
    with_credit = tiers.choose(tmp_path, credits=own)["cheap"]["scored"][0]
    assert without["credits_used"] == 0 and with_credit["credits_used"] > 0 and with_credit["money_spent"] == 0


def test_choose_offers_only_configured_providers(tmp_path):
    import shutil
    for name in ("tier_arms.csv", "tier_prices.csv", "tier_credits.csv", "tier_measurements.csv"):
        shutil.copy(registry.DATA / name, tmp_path / name)
    (tmp_path / "tier_measurements.csv").write_text("tier,provider,model,cases,passed,tokens_in,tokens_out,source,measured_on\n")   # none measured
    got = tiers.choose(tmp_path, available={"gemini"})
    assert got["cheap"]["arm"] == ("gemini", "gemini-2.5-flash-lite") and "cheapest priced available" in got["cheap"]["reason"]
    assert got["mid"]["arm"] == ("gemini", "gemini-2.5-flash") and got["strong"]["arm"] is None
    (tmp_path / "tier_measurements.csv").write_text(
        "tier,provider,model,cases,passed,tokens_in,tokens_out,source,measured_on\n"
        "cheap,anthropic,claude-haiku-5-5,10,9,1000000,200000,test,2026-10-30\n"
        "cheap,gemini,gemini-3.1-flash-lite,10,9,1000000,200000,test,2026-10-30\n")
    both = tiers.choose(tmp_path)
    assert both["cheap"]["arm"] == ("anthropic", "claude-haiku-5-5")          # same passing work, the cheaper arm wins


def test_the_shipped_aime_measurements_decide_when_only_other_providers_are_configured():
    """The recorded model_quality_aime rows are used: without Anthropic the cheap tier goes to the arm with the most passing work per cost."""
    got = tiers.choose(available={"openai", "gemini", "deepseek"})
    assert got["cheap"]["arm"] == ("openai", "gpt-5-nano") and "passing cases per cost" in got["cheap"]["reason"]
    assert got["mid"]["arm"] == ("gemini", "gemini-2.5-flash")
