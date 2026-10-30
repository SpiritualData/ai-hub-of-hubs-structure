"""The watch-for-risk engine: digest, signal parsing, the safe default, and assembly with a consumer's prompt as data."""
import hubofhubs
from hubofhubs import risk

PROMPT = "WATCH\n{digest}"


class Provider:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def plan(self, prompt, *, model, tool_schema, step=None):
        self.prompts.append((prompt, model, tool_schema, step))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def render(digest):
    return PROMPT.format(digest=digest)


def test_the_digest_shows_the_request_and_stays_within_its_budget():
    text = risk.build_digest(user_message="add a goal", goal_condition="add the goal to the plan", step=2, max_steps=5,
                             operations=["[read] a -> b"] * 40, recent_conversation=["x" * 400] * 9, char_budget=600)
    assert text.startswith("CURRENT USER REQUEST: add a goal") and "RESOLVED AS: add the goal" in text
    assert len(text) <= 600 and "PASS: 2 of 5" in text


def test_a_refusal_in_the_prior_escalations_outlives_the_operations_when_the_digest_must_shed():
    text = risk.build_digest(user_message="q", step=1, max_steps=2, prior_escalations=["declined: send the mail"],
                             operations=["[read] " + "y" * 150] * 6, recent_conversation=["turn"] * 3, char_budget=420)
    assert "declined: send the mail" in text and "OPERATIONS THIS TURN (" not in text


def test_a_signal_is_parsed_and_the_hint_is_only_for_a_redirect():
    assert risk.oversee_with(Provider({"signal": "redirect", "hint": "h" * 300, "reason": "r"}), "m", "d", render).hint == "h" * 200
    assert risk.oversee_with(Provider({"signal": "answer_now", "hint": "ignored"}), "m", "d", render).hint == ""


def test_every_failure_degrades_to_a_degraded_proceed():
    for reply in (RuntimeError("down"), "not a dict", {"signal": "panic"}):
        got = risk.oversee_with(Provider(reply), "m", "d", render)
        assert got.signal == "proceed" and got.degraded


def test_the_consumers_prompt_is_the_only_prompt_and_the_call_names_the_judge_step():
    provider = Provider({"signal": "proceed"})
    risk.oversee_with(provider, "tier-x", "DIGEST", render)
    prompt, model, tool, step = provider.prompts[0]
    assert prompt == "WATCH\nDIGEST" and model == "tier-x" and step == "judge" and tool is risk.OVERSEE_TOOL


def test_assembly_builds_the_overseer_with_the_consumers_prompt_and_names_the_layer():
    config = hubofhubs.AssemblyConfig(solutions=("watch-for-risk",), selections={"watch-for-risk": "overseer"},
                                 options={"watch-for-risk": {"render": render}})
    system = hubofhubs.assemble(config)
    watcher = system["watch-for-risk"]
    assert isinstance(watcher, hubofhubs.seats.RiskWatching)
    assert watcher.oversee(Provider({"signal": "escalate_human", "reason": "Do you want me to proceed?"}), "m", watcher.digest(
        user_message="u", step=1, max_steps=1)).signal == "escalate_human"
    assert "overseer" in system.reasons[0] and "consumer selections" in system.reasons[0]
    assert "overseer" in hubofhubs.names("watch-for-risk")


def test_with_no_prompt_there_is_no_policy_and_no_model_call():
    provider = Provider({"signal": "escalate_human"})
    got = risk.RunOverseer().oversee(provider, "m", "d")
    assert got.signal == "proceed" and got.degraded and provider.prompts == []
