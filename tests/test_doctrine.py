"""Situational doctrine: rules as data, a situation as facts, an ordered prompt with its size and the ids in and out."""
import hubofhubs.doctrine as doctrine
from hubofhubs.doctrine import Rule, applies, assemble_doctrine, check_rules, estimate_tokens

RULES = (
    Rule("core", "CORE\n"),
    Rule("deep", "DEEP\n", {"deep": True, "mode": "normal"}),
    Rule("either", "EITHER\n", [{"mode": "brainstorm"}, {"run": True}]),
    Rule("tail", "TAIL\n", {}),
)


def test_an_empty_condition_always_applies_and_text_keeps_the_order_given():
    got = assemble_doctrine(RULES, {"deep": True, "mode": "normal", "run": False})
    assert got.text == "CORE\nDEEP\nTAIL\n"
    assert got.included == ("core", "deep", "tail") and got.excluded == ("either",)


def test_every_fact_of_a_clause_must_match():
    assert not applies(RULES[1], {"deep": True, "mode": "brainstorm"})
    assert not applies(RULES[1], {"deep": False, "mode": "normal"})


def test_a_list_of_values_means_any_of_them_and_a_list_of_clauses_means_any_clause():
    rule = Rule("r", "R", {"mode": ["normal", "hold_off"]})
    assert applies(rule, {"mode": "hold_off"}) and not applies(rule, {"mode": "brainstorm"})
    assert applies(RULES[2], {"mode": "normal", "run": True}) and applies(RULES[2], {"mode": "brainstorm", "run": False})
    assert not applies(RULES[2], {"mode": "normal", "run": False})


def test_an_unknown_fact_fails_open_so_a_rule_leaves_only_on_a_positive_reason():
    assert applies(RULES[1], {})
    assert applies(RULES[1], {"deep": None, "mode": None})
    assert applies(RULES[2], {})


def test_tokens_are_the_estimate_of_the_assembled_text():
    got = assemble_doctrine(RULES, {})
    assert got.tokens == estimate_tokens(got.text) and estimate_tokens("") == 0
    assert estimate_tokens("x" * 7) == 2 and estimate_tokens("x" * 8, chars_per_token=4) == 2
    assert assemble_doctrine(RULES, {}, chars_per_token=1).tokens == len(got.text)


def test_a_smaller_situation_gives_a_smaller_prompt():
    full = assemble_doctrine(RULES, {})
    small = assemble_doctrine(RULES, {"deep": False, "mode": "normal", "run": False})
    assert small.tokens < full.tokens and set(small.included) < set(full.included)


def test_check_rules_names_a_repeated_id_and_a_fact_the_situation_does_not_declare():
    assert check_rules(RULES, ("deep", "mode", "run")) == []
    bad = (Rule("a", "A"), Rule("a", "B", {"typo": 1}), Rule("", "C"))
    problems = check_rules(bad, ("mode",))
    assert any("repeated" in p for p in problems) and any("typo" in p for p in problems)
    assert len(problems) == 3


def test_the_module_has_no_consumer_and_reads_no_environment():
    source = open(doctrine.__file__).read()
    assert "os.environ" not in source and "getenv" not in source
