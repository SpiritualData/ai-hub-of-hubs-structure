"""Tool-schema compaction and closed-vocabulary normalizing."""
from hubofhubs.orchestrate.plan import PlanDecision
from hubofhubs.orchestrate.schema import compact_schema, normalize_choice, strip_schema_descriptions

TOOL = {"name": "decide", "description": "d", "input_schema": {"type": "object", "properties": {
    "a": {"type": "string", "description": "about a"},
    "hand": {"type": "object", "description": "keep me", "properties": {"x": {"type": "string", "description": "x"}}}}}}


def test_every_description_is_stripped_and_the_input_is_untouched():
    out = strip_schema_descriptions(TOOL)
    assert "description" not in repr(out) and TOOL["input_schema"]["properties"]["a"]["description"] == "about a"


def test_a_named_description_survives_the_compact_schema():
    out = compact_schema(TOOL, ("hand",))
    assert out["input_schema"]["properties"]["hand"]["description"] == "keep me"
    assert "description" not in out["input_schema"]["properties"]["a"]
    assert "description" not in compact_schema(TOOL)["input_schema"]["properties"]["hand"]


def test_a_choice_is_normalized_or_not_given():
    assert normalize_choice(" Act ", ("act", "ask")) == "act"
    assert normalize_choice("maybe", ("act", "ask")) is None and normalize_choice(None, ("act",)) is None


def test_the_decision_value_defaults_are_pinned():
    d = PlanDecision(action="answer")
    assert (d.reads, d.deep_subtasks, d.pending_read, d.facts_read, d.done_evidence) == ([], [], [], [], [])
    assert d.answer_contains_work_to_execute is False and d.act_declined is False and d.confidence is None
