"""The answering mixin on a stand-in host: the flow runs on the kit's text and renderers, and falls back safely."""
import logging
from types import SimpleNamespace as NS

from hubofhubs.orchestrate.answer import AnswerKit, AnsweringMixin
from hubofhubs.orchestrate.plan import PlanDecision

VOICE = "VOICE"


def make_kit(**over):
    base = dict(
        reply_voice_system=VOICE, synthesize_after_deep="D {request}|{proposal}|{result}|{standard_line}",
        synthesize_task_report="R {request}|{proposal}|{result}|{standard_line}",
        synthesize_after_queued="Q {request}|{proposal}|{result}", subquestion_focus="focus {sub}",
        merge_prompt="merge {message} :: {merged}", merged_part="S {q} / A {a}", done_standard_line="STD {standard};",
        queued_note="queued.", report_goal="report {request}", none_marker="(none)", handoff_marker="(handoff)",
        grounding_block=lambda ctx, gathered, partial: f"G[{ctx}|{len(gathered)}|{partial}]",
        grounding_tail=lambda gathered, partial: f"T[{len(gathered)}]", grounding_layer=lambda ctx: f"L[{ctx}]",
        layered_blocks=lambda persona, context, tail: [persona, context, tail], accepts_layers=lambda fn: True,
        log=logging.getLogger("test-answer"))
    base.update(over)
    return AnswerKit(**base)


class Provider:
    def __init__(self, reply="ok", fail=False):
        self.calls, self.reply, self.fail = [], reply, fail

    def answer(self, messages, model=None, system=None, **kw):
        self.calls.append({"messages": messages, "system": system, **kw})
        if self.fail:
            raise RuntimeError("down")
        return self.reply


class Host(AnsweringMixin):
    def __init__(self, provider, kit=None):
        self.provider, self.answer_kit = provider, kit or make_kit()
        self.cfg = NS(max_subquestions=3, max_parallel=2)
        self.registry = NS(resolve_tier=lambda tier: f"model-{tier}")
        self.verdict = ({"claims_unexecuted": True}, None)

    def get_provider_for_model(self, model):
        return self.provider

    def verify_goal(self, goal, brief, output, **kw):
        self.goal = goal
        return self.verdict


def test_the_model_comes_from_the_hint_then_the_plan_then_the_default():
    host = Host(Provider())
    assert host.answer_model(PlanDecision(action="answer", model_tier="plan"), "dflt", hint="hint") == "model-hint"
    assert host.answer_model(PlanDecision(action="answer", model_tier="plan"), "dflt") == "model-plan"
    assert host.answer_model(PlanDecision(action="answer"), "dflt") == "model-dflt"


def test_a_grounded_answer_uses_the_voice_directive_and_layers():
    provider = Provider("reply")
    host = Host(provider)
    out = host.grounded_answer("q?", "transcript", "ctx", [{"a": 1}], "m", False, rep_preamble="persona", reply_directive="DIR")
    call = provider.calls[0]
    assert out == "reply" and call["system"] == f"{VOICE}\n\nDIR"
    assert call["layers"] == ["persona", "L[ctx]", "transcript\n\nT[1]\n\nq?"]
    assert [m["content"] for m in call["messages"]] == ["persona", "transcript", "G[ctx|1|False]", "q?"]


def test_native_blocks_skip_the_layers_and_ride_with_the_question():
    provider = Provider()
    Host(provider).grounded_answer("q?", "", "", [], "m", False, native_blocks=[{"type": "image"}])
    call = provider.calls[0]
    assert "layers" not in call and call["messages"][-1]["content"] == [{"type": "image"}, {"type": "text", "text": "q?"}]


def test_the_after_deep_reply_folds_the_output_and_falls_back_to_it():
    provider = Provider("  folded  ")
    host = Host(provider)
    assert host.synthesize_after_deep("do x", prior_answer="", deep_output=" done ", transcript="", model="m", standard="goal") == "folded"
    assert provider.calls[0]["messages"][-1]["content"] == "D do x|(none)|done|STD goal;"
    assert Host(Provider(fail=True)).synthesize_after_deep("x", prior_answer="p", deep_output="out", transcript="", model="m") == "out"
    assert Host(Provider(fail=True)).synthesize_after_deep("x", prior_answer="p", deep_output="", transcript="", model="m") == "p"


def test_the_queued_reply_falls_back_to_the_kits_note():
    assert Host(Provider(fail=True)).synthesize_after_queued("x", prior_answer="prior", handoff_output="", transcript="", model="m") == "prior\n\nqueued."
    provider = Provider("ok")
    Host(provider).synthesize_after_queued("x", prior_answer="", handoff_output="", transcript="", model="m")
    assert provider.calls[0]["messages"][-1]["content"] == "Q x|(none)|(handoff)"


def test_a_task_report_uses_its_template_and_returns_the_raw_output_on_failure():
    provider = Provider("report")
    assert Host(provider).synthesize_task_report("req", "raw") == "report"
    assert provider.calls[0]["messages"][-1]["content"].startswith("R req|")
    assert Host(Provider(fail=True)).synthesize_task_report("req", "raw") == "raw"


def test_the_claim_check_reads_the_verdict_and_none_means_it_could_not_run():
    host = Host(Provider())
    assert host.report_claims_unbacked("req", "text", None) is None
    assert host.report_claims_unbacked("req", "text", object()) is True and host.goal == "report req"
    host.verdict = (None, "err")
    assert host.report_claims_unbacked("req", "text", object()) is None


def test_subquestions_fan_out_then_merge_and_a_single_one_is_a_plain_answer():
    provider = Provider("part")
    host = Host(provider)
    assert host.answer_subquestions("m", "", "ctx", [], "m1", ["a"]) == "part"
    provider.calls.clear()
    out = host.answer_subquestions("msg", "", "ctx", [], "m1", ["a", "b"])
    assert out == "part" and len(provider.calls) == 3
    merge = provider.calls[-1]["messages"][-1]["content"]
    assert merge.startswith("merge msg :: S a / A part\n\nS b / A part")


def test_when_every_subanswer_fails_the_grounded_answer_runs():
    provider = Provider(fail=True)
    host = Host(provider)
    try:
        host.answer_subquestions("m", "", "ctx", [], "m1", ["a", "b"])
    except RuntimeError:
        pass
    assert len(provider.calls) == 3   # two sub-answers, then the grounded fallback
