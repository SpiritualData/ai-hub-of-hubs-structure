"""The composite context assembler: several assemblers run as one, and a broken member never breaks the turn. Offline."""
from hubofhubs import AssemblyConfig, assemble, resolve
from hubofhubs.ports.context import AssembledContext
from hubofhubs.recall.composite_assembler import CompositeContextAssembler, find_assembler
from hubofhubs.seats import ContextAssembling


class Member:
    def __init__(self, view, ids=(), hint=None):
        self.view, self.ids, self.hint, self.recorded = view, list(ids), hint, []

    def assemble(self, task_text, *, meta=None, on_event=None):
        return AssembledContext(context_view=self.view, card_ids=self.ids, model_tier_hint=self.hint)

    def record(self, task_text, outcome):
        self.recorded.append(task_text)

    def render_card(self, card_id, *, meta=None):
        return f"card {card_id}" if card_id in self.ids else None


class Broken:
    def assemble(self, task_text, *, meta=None, on_event=None):
        raise RuntimeError("down")

    def record(self, task_text, outcome):
        raise RuntimeError("down")


def test_it_satisfies_the_seat():
    assert isinstance(CompositeContextAssembler([]), ContextAssembling)


def test_views_are_joined_in_order_and_ids_are_merged_and_the_first_hint_wins():
    out = CompositeContextAssembler([Member("one", ["a"], "fast"), Member(""), Member("two", ["b"], "best")]).assemble("task")
    assert out.context_view == "one\n\ntwo" and out.card_ids == ["a", "b"] and out.model_tier_hint == "fast"


def test_a_broken_member_costs_only_its_own_part():
    out = CompositeContextAssembler([Broken(), Member("kept", ["k"])]).assemble("task")
    assert out.context_view == "kept" and out.card_ids == ["k"]


def test_record_reaches_every_member_best_effort():
    good = Member("x")
    CompositeContextAssembler([Broken(), good]).record("task", {})
    assert good.recorded == ["task"]


def test_events_are_emitted_by_the_composite_only():
    seen = []
    CompositeContextAssembler([Member("x", ["a"])]).assemble("t", on_event=lambda kind, data: seen.append((kind, data["assembler"])))
    assert seen == [("arm_done", "Member")]


def test_render_card_asks_members_until_one_can():
    assert CompositeContextAssembler([Member("x", ["a"]), Member("y", ["b"])]).render_card("b") == "card b"
    assert CompositeContextAssembler([Broken(), Member("x")]).render_card("zz") is None


def test_find_assembler_unwraps_the_known_wrapper_shapes():
    inner = Member("x")
    assert find_assembler(CompositeContextAssembler([Broken(), inner]), lambda a: a is inner) is inner
    assert find_assembler(inner, lambda a: False) is None


def test_the_arm_is_resolved_by_name_through_the_hub():
    assert resolve("context-assembler", "composite") is CompositeContextAssembler
    system = assemble(AssemblyConfig(solutions=("context-assembler",), selections={"context-assembler": "composite"},
                                     options={"context-assembler": {"assemblers": [Member("x")]}}))
    assert system.get("context-assembler").assemble("t").context_view == "x"
