"""The deep-run tier rule: the cheapest tier measured good enough by default; a person's tier (now, then standing guidance) raises it; a failed task escalates one rung
with a recorded reason, for that task only; a sub-agent runs on its own default. Small planted measurements and the table on disk."""
import pytest

from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers as rt

RULES = rt.read_rules()
TABLE = rt.read_table()
DEEP = rt.deep_run_roles(RULES)


def measure(**rates):
    """Planted measurements: a tier maps to (passed, total)."""
    return {t: dict(passed=p, total=n, arms=1, first="2026-11-11", last="2026-11-11") for t, (p, n) in rates.items()}


def test_the_bar_is_stated_once_with_its_source_and_the_source_still_says_it():
    bar = [r for r in RULES if r["part"] == "sufficiency" and r["key"] == "pass_rate_bar"]
    assert len(bar) == 1 and float(bar[0]["value"]) == 0.66 and "metric-delegated-agent-sessions-hard" in bar[0]["reason"]
    source = rt.STANDINGS.with_name("metrics.csv").read_text(encoding="utf-8")
    hard = next(line for line in source.splitlines() if line.startswith("metric-delegated-agent-sessions-hard,"))
    assert "min-pass-rate=0.66" in hard


def test_the_default_is_the_cheapest_tier_that_meets_the_bar_on_the_recorded_cases():
    got = rt.sufficient_tier(RULES, measure(fast=(24, 27)))
    assert got["tier"] == "fast" and "0.889" in got["note"]
    assert rt.sufficient_tier(RULES, measure(fast=(17, 27), balanced=(25, 27), quality=(27, 27)))["tier"] == "balanced"      # fast 0.63 is under the bar
    assert rt.sufficient_tier(RULES, measure(fast=(18, 27)))["tier"] == "fast"                                              # 0.667 meets it


def test_a_tier_with_no_measurement_is_skipped_and_the_row_says_so():
    got = rt.sufficient_tier(RULES, measure(balanced=(25, 27)))
    assert got["tier"] == "balanced" and "no measurement for fast, quality" in got["note"] and "cheapest measured tier" in got["note"]
    below = rt.sufficient_tier(RULES, measure(fast=(10, 27)))
    assert below["tier"] == "balanced" and "no measured tier meets the bar" in below["note"]       # the rung above the highest measured one
    assert rt.sufficient_tier(RULES, {})["tier"] is None


def test_the_measurement_is_read_from_the_recorded_standings_per_tier():
    got = rt.measured_pass_rates()
    assert set(got) == {"fast"} and got["fast"]["total"] >= 27 and 0 < got["fast"]["passed"] <= got["fast"]["total"]
    assert rt.measured_pass_rates(rt.STANDINGS.with_name("no_such_file.json")) == {}


def test_every_deep_run_role_lands_on_the_cheap_sufficient_tier_by_default():
    assert {"deep_work_gather", "deep_work_implementation", "deep_work_structure", "deep_work_review", "main_session", "sub_agent", "after_check_resume"} <= set(DEEP)
    for role in (r for r in DEEP if not rt.own_evidence_for(RULES, r)):        # file_editing is judged on its own evidence, below
        assert rt.choose_tier(role, table=TABLE, rules=RULES).tier == "fast" and rt.choose_tier(role, table=TABLE, rules=RULES).source == "default", role
    assert rt.tier_for_task("", table=TABLE) == "fast"         # the tier of a plain ahohs work request


def test_the_constraints_of_the_per_call_roles_are_unchanged():
    assert TABLE["request_classification"]["tier"] == "fast" and TABLE["response_writing"]["tier"] == "balanced" and TABLE["structure-watch"]["tier"] == "best"
    assert not set(DEEP) & {r for r, row in TABLE.items() if row["constraint"]}


def test_an_explicit_ask_in_the_current_request_raises_the_tier():
    choice = rt.choose_tier("main_session", requested="quality", table=TABLE, rules=RULES)
    assert (choice.tier, choice.source) == ("quality", "current_input") and choice.record()["tier_source"] == "current_input"
    assert rt.choose_tier("main_session", requested="strong", table=TABLE, rules=RULES).tier == "quality"
    with pytest.raises(ValueError):
        rt.choose_tier("main_session", requested="enormous", table=TABLE, rules=RULES)


def test_standing_guidance_raises_the_tier_when_the_request_names_none():
    asked = []

    def guidance(role):
        asked.append(role)
        return "balanced"
    choice = rt.choose_tier("main_session", standing=guidance, table=TABLE, rules=RULES)
    assert (choice.tier, choice.source) == ("balanced", "standing_guidance") and asked == ["main_session"]
    assert rt.choose_tier("main_session", standing=lambda role: "", table=TABLE, rules=RULES).source == "default"        # guidance with nothing to say changes nothing
    assert rt.tier_for_task("structure", standing=lambda role: "quality", table=TABLE) == "quality"


def test_the_current_request_beats_standing_guidance_and_guidance_never_reaches_a_role_a_person_may_not_set():
    choice = rt.choose_tier("main_session", requested="fast", standing=lambda role: "quality", table=TABLE, rules=RULES)
    assert (choice.tier, choice.source) == ("fast", "current_input")
    assert rt.choose_tier("request_classification", requested="best", standing=lambda role: "best", table=TABLE, rules=RULES).tier == "fast"
    assert rt.choose_tier("sub_agent", requested="best", standing=lambda role: "best", table=TABLE, rules=RULES).source == "default"


def test_an_escalation_needs_a_specific_reason_and_a_known_signal():
    start = rt.choose_tier("main_session", table=TABLE, rules=RULES)
    for bad in ("", "   ", "review", "after check"):
        with pytest.raises(ValueError):
            rt.escalate(start, "review" if bad != "after check" else "after_check", bad, RULES)
    with pytest.raises(ValueError):
        rt.escalate(start, "a hunch", "the diff touched four modules the tier did not read", RULES)


def test_an_escalation_moves_one_rung_records_the_reason_and_stops_at_quality():
    start = rt.choose_tier("main_session", table=TABLE, rules=RULES)
    up = rt.escalate(start, "after_check", "the code check failed twice on the same type error the tier did not find", RULES)
    assert (up.tier, up.source, up.from_tier) == ("balanced", "escalation", "fast")
    assert up.record() == {"tier": "balanced", "tier_source": "escalation", "tier_reason": "after_check: the code check failed twice on the same type error the tier did not find",
                           "tier_from": "fast"}
    top = rt.escalate(up, "review", "the review found the migration order wrong", RULES)
    assert top.tier == "quality"
    with pytest.raises(ValueError):
        rt.escalate(top, "review", "still wrong in the same place", RULES)                      # no rung above quality
    best = rt.choose_tier("main_session", requested="best", table=TABLE, rules=RULES)
    with pytest.raises(ValueError):
        rt.escalate(best, "review", "the person asked for best and it still failed", RULES)     # best is not a rung the planner climbs
    with pytest.raises(ValueError):
        rt.escalate(rt.choose_tier("request_classification", table=TABLE, rules=RULES), "review", "a label was wrong", RULES)     # a per-call role is not escalated


def test_an_escalation_is_never_sticky_the_next_task_starts_from_the_default_again():
    first = rt.choose_tier("main_session", table=TABLE, rules=RULES)
    rt.escalate(first, "stop_decision", "the run could not meet the milestone on this tier", RULES)
    again = rt.choose_tier("main_session", table=TABLE, rules=RULES)
    assert again == first and again.tier == "fast"
    assert rt.tier_for_task("implementation", table=TABLE) == "fast"


def test_a_sub_agent_runs_on_its_own_default_unless_the_main_session_asks_for_more_with_a_reason():
    assert rt.sub_agent_choice(table=TABLE, rules=RULES).tier == "fast"
    main = rt.choose_tier("main_session", requested="quality", table=TABLE, rules=RULES)
    assert main.tier == "quality" and rt.sub_agent_choice(table=TABLE, rules=RULES).tier == "fast"       # the main session's tier does not carry down
    ask = rt.sub_agent_choice("balanced", "the part rewrites the planner and must read all of its callers", TABLE, RULES)
    assert (ask.tier, ask.source) == ("balanced", "main_session_ask") and "planner" in ask.record()["tier_reason"]
    with pytest.raises(ValueError):
        rt.sub_agent_choice("balanced", "", TABLE, RULES)


def test_the_run_record_carries_the_tier_choice_keys():
    keys = rt.escalate(rt.choose_tier("main_session", table=TABLE, rules=RULES), "review", "the reviewer found an unread file", RULES).record()
    assert {"tier", "tier_source", "tier_reason"} <= set(keys)


# File editing: the cheapest-sufficient rule on its own measurement (the component file_edit_goals), the same bar.
INPUTS = {i["role"]: i for i in rt.read_inputs()}
FAST_EDIT_ROW = dict(component="file_edit_goals", impl="fast_edit", sample="", date="2026-10-31", passed="29", cases="30", model="m-fast-then")


def results_file(tmp_path, *rows):
    path = tmp_path / "results.csv"
    cols = ("date", "component", "impl", "cases", "passed", "sample", "model")
    path.write_text(",".join(cols) + "\n" + "".join(",".join(str(r.get(c, "")) for c in cols) + "\n" for r in rows), encoding="utf-8")
    return path


def test_file_editing_follows_the_rule_with_its_own_evidence_and_the_same_bar_stated_once():
    assert "file_editing" in DEEP and rt.own_evidence_for(RULES, "file_editing") == dict(component="file_edit_goals", arms={"fast": "fast_edit"})
    assert [r["value"] for r in RULES if r["part"] == "sufficiency" and r["key"] == "pass_rate_bar"] == ["0.66"]          # no second bar
    assert rt.own_evidence_for(RULES, "main_session") == {}


def test_file_editing_default_resolves_to_fast_when_a_current_run_of_the_fast_tier_meets_the_bar(tmp_path):
    path = results_file(tmp_path, dict(FAST_EDIT_ROW, passed="30", date="2026-10-30"), FAST_EDIT_ROW, dict(FAST_EDIT_ROW, impl="none", passed="0", model="none"),
                        dict(FAST_EDIT_ROW, sample="sample:3", passed="0", cases="3"))
    own = rt.own_pass_rates(RULES, "file_editing", "2026-11-11", {"fast": "m-fast-then"}, path)
    assert own == ({"fast": dict(passed=29, total=30, arms=1, first="2026-10-31", last="2026-10-31")}, [])         # the latest full run; the zero bound and samples are not a tier
    row = rt.role_row(INPUTS["file_editing"], RULES, {}, {}, "2026-11-11", {"file_editing": "quality"}, own=own)
    assert row["tier"] == "fast" and row["evidence"].startswith("sufficiency rule") and "file_edit_goals" in row["evidence"] and "fast 29 of 30" in row["evidence"]
    assert rt.sufficient_tier(RULES, own[0], what="x")["bar"] == 0.66
    below = rt.own_pass_rates(RULES, "file_editing", "2026-11-11", {"fast": "m-fast-then"}, results_file(tmp_path, dict(FAST_EDIT_ROW, passed="19")))
    assert rt.role_row(INPUTS["file_editing"], RULES, {}, {}, "2026-11-11", {"file_editing": "fast"}, own=below)["tier"] == "balanced"     # 0.633 is under the bar: one rung above


def test_file_editing_evidence_from_another_model_or_past_the_expiry_is_not_used_and_the_row_says_so(tmp_path):
    path = results_file(tmp_path, FAST_EDIT_ROW)
    other = rt.own_pass_rates(RULES, "file_editing", "2026-11-11", {"fast": "m-fast-now"}, path)
    assert other[0] == {} and "different model" in other[1][0]
    stale = rt.own_pass_rates(RULES, "file_editing", "2027-02-01", {"fast": "m-fast-then"}, path)
    assert stale[0] == {} and "past the 90 day expiry" in stale[1][0]
    assert rt.own_pass_rates(RULES, "file_editing", "2026-11-11", {"fast": "m-fast-then"}, tmp_path / "none.csv")[0] == {}
    row = rt.role_row(INPUTS["file_editing"], RULES, {}, {}, "2026-11-11", {"file_editing": "quality"}, own=other)
    assert row["tier"] == "quality" and row["evidence"].startswith("STALE OR MISSING") and "previous tier quality is kept" in row["evidence"]     # the rule's fallback, no invented measurement


def test_file_editing_on_disk_uses_its_own_evidence_and_says_what_it_found():
    row = TABLE["file_editing"]
    assert row["person_may_set"] == "yes" and row["constraint"] == "" and "file_edit_goals" in row["evidence"] and "29 of 30" in row["evidence"]
    assert "different model" in row["evidence"] or row["tier"] == "fast"      # recorded under another model than the fast tier names: not used, so the tier is kept
    assert not set(rt.measured_pass_rates()) - {"fast"} and "deep-work" not in row["evidence"]


def test_a_person_can_raise_file_editing_and_a_failed_edit_escalates_one_rung_with_a_reason():
    choice = rt.choose_tier("file_editing", requested="best", table=TABLE, rules=RULES)
    assert (choice.tier, choice.source) == ("best", "current_input")
    assert rt.choose_tier("file_editing", standing=lambda role: "balanced", table=TABLE, rules=RULES).source == "standing_guidance"
    default = rt.choose_tier("file_editing", table=TABLE, rules=RULES)
    assert default.source == "default" and "sufficiency bar" in default.reason
    low = rt.TierChoice("file_editing", "fast", "default")
    up = rt.escalate(low, "after_check", "the edit missed the second call site its own tests exercise", RULES)
    assert (up.tier, up.source, up.from_tier) == ("balanced", "escalation", "fast")


def test_connected_system_operations_stays_on_quality_by_a_stated_constraint_and_a_person_can_set_higher():
    cons = rt.constraints_for(RULES, "work", "connected_system_operations")
    assert [(n, a) for n, a, _ in cons] == [("significant_downstream_effect_quality_min", "min:quality")]
    assert "significant downstream effect" in cons[0][2] and "no measurement" in cons[0][2]
    row = TABLE["connected_system_operations"]
    assert row["tier"] == "quality" and row["constraint"] == "significant_downstream_effect_quality_min" and row["person_may_set"] == "yes"
    assert "connected_system_operations" not in DEEP                                                  # no rule or evidence lowers it
    assert rt.apply_constraints("fast", cons) == rt.apply_constraints("balanced", cons) == "quality"   # even a metric that picked lower is raised to quality
    assert rt.apply_constraints("best", cons) == "best"
    assert rt.tier_for("connected_system_operations", "best", TABLE) == "best" and rt.tier_for("connected_system_operations", table=TABLE) == "quality"
    with pytest.raises(ValueError):
        rt.escalate(rt.TierChoice("connected_system_operations", "quality", "default"), "review", "the operation touched the wrong record", RULES)      # not a deep-run role
