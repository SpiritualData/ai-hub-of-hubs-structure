"""The flow of the hub, run for real over fakes: every container's composition calls the entry point of each solution it uses, a solution with no arm
yet comes back as a pending step with its reason (never as made-up output), and the quality profile is resolved before Response Quality judges."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hubofhubs  # noqa: E402
from esoi.entry import Pending  # noqa: E402
from hubofhubs import quality  # noqa: E402
from hubofhubs.steps import NO_ARM  # noqa: E402
from test_oneline import whole_hub  # noqa: E402

NO_ARM_SOLUTIONS = ("ai-representatives", "judgment-calls", "feedback-learning", "prioritization", "esoi-application", "metric-translation",
                    "goal-completion", "context-intake", "planner", "delegation", "response-writer", "long-term-memory", "hold-objectives",
                    "guidance", "offer-intuition", "role-understanding", "personal-data-locations", "connect-any-integration")


def walk(steps):
    for step in steps:
        yield step
        yield from walk(step.get("steps", ()))


def test_the_self_responds_through_every_container_and_reports_what_has_no_arm(tmp_path):
    result = hubofhubs.run("hub-of-hubs", "what is the latest Rust release?", **whole_hub(tmp_path))
    assert result.answer == "1.90.0"                        # the interim answer of the existing arms
    top = [(s["solution"], s["status"]) for s in result.steps]
    assert top == [("the-consciousness", "done"), ("the-body", "done"), ("the-intelligence", "done"), ("assemble-the-whole", "done"),
                   ("the-consciousness", "done")]
    assert result.steps[-1]["steps"] == [{"solution": "feedback-learning", "status": "skipped", "reason": "no feedback was given"}]   # nothing to learn from
    every = {s["solution"]: s for s in walk(result.steps)}
    for sid in ("planner", "delegation", "response-writer", "context-intake", "higher-mind", "metric-translation", "goal-completion", "offer-intuition"):
        assert sid in every or any(sid == x["solution"] for x in walk(result.steps)), sid
    for sid in ("planner", "context-intake", "response-writer", "goal-completion", "metric-translation", "ai-representatives", "connect-any-integration"):
        assert every[sid]["status"] == "pending" and every[sid]["reason"] == NO_ARM, (sid, every[sid])
    assert every["response-quality"]["status"] == "skipped"      # no response was written, so nothing is judged
    assert result.to_dict()["steps"] == list(result.steps)


@pytest.mark.parametrize("sid", NO_ARM_SOLUTIONS)
def test_a_solution_with_no_arm_has_its_interface_and_says_no_arm_yet(sid):
    with pytest.raises(Pending) as raised:
        hubofhubs.run(sid, environ={})
    assert {r.kind for r in raised.value.reasons} == {"provided"} and "no arm yet" in str(raised.value)


class Planner:
    def plan(self, request, context=None, target=None, guidance=None):
        return [{"piece": "read the file", "sub_goal": "file read"}, {"piece": "delete the old backup folder", "sub_goal": "folder gone"}]


class Delegation:
    def __init__(self):
        self.handed = []

    def delegate(self, pieces, authority=None):
        self.handed.append((list(pieces), authority))
        return [{"piece": p["piece"], "result": "done"} for p in pieces]


class Writer:
    def write(self, results, profile=None):
        return "; ".join(r["piece"] for r in results)


class Intake:
    def take(self, request, prepared=None, outside=None):
        return {"view": request}


class Watch:
    def digest(self, **fields):
        return fields["plan_action"]

    def oversee(self, provider, model, digest):
        raise NotImplementedError

    def watch(self, digest, model=""):
        class Signal:
            signal = "escalate_human" if "delete" in digest else "proceed"
        return Signal()


class Judgment:
    def decide(self, signal, person=""):
        return {"decision": "decline" if signal["signal"] == "escalate_human" else "proceed"}


def test_the_mind_checks_the_risk_signal_and_the_persons_decision_before_it_delegates():
    delegation = Delegation()
    provided = {"planner": Planner(), "delegation": delegation, "response-writer": Writer(), "context-intake": Intake(), "watch-for-risk": Watch(),
                "judgment-calls": Judgment()}
    out = hubofhubs.run("reason-and-answer", {"request": "tidy up", "authority": {"person": "p1"}}, provided=provided, environ={})
    assert delegation.handed == [([{"piece": "read the file", "sub_goal": "file read"}], {"person": "p1"})]    # the risky piece was declined for this person
    assert out["text"] == "read the file"
    order = [(s["solution"], s["status"]) for s in out["steps"]]
    assert order[0] == ("context-intake", "done") and order[1] == ("planner", "done") and order[-2:] == [("delegation", "done"), ("response-writer", "done")]
    assert [s for s, _ in order].count("judgment-calls") == 2


class Absent:
    """A seat that has no arm: reading any method of it fails the way an unbuilt seat does."""
    def __getattr__(self, name):
        from esoi.assemble import AssemblyError
        raise AssemblyError("no arm yet for this seat")


def test_a_piece_whose_risk_cannot_be_checked_is_not_handed_on():
    delegation = Delegation()
    mind = hubofhubs.resolve("reason-and-answer", "composition")(Intake(), Planner(), delegation, Writer(), Absent(), Judgment())
    out = mind.think("tidy up")
    assert delegation.handed == [([], {})]
    assert [s["status"] for s in out["steps"] if s["solution"] == "watch-for-risk"] == ["pending", "pending"]


def test_the_default_profile_lists_the_public_criteria_and_fixes_no_number():
    names = [c.name for c in quality.DEFAULT_PROFILE.criteria]
    assert names == ["helpfulness", "faithfulness to evidence", "groundedness", "concision", "tone fit", "safety"]
    assert all(c.weight is None and c.target is None for c in quality.DEFAULT_PROFILE.criteria)
    assert quality.resolve_profile() is quality.DEFAULT_PROFILE


def test_the_profile_is_resolved_from_the_representative_guidance_and_prioritization():
    mine = quality.QualityProfile("mine", (quality.Criterion("concision", "short", 0.5, 0.9),))
    resolved = quality.resolve_profile({"quality_profile": mine}, {"quality_criteria": quality.QualityProfile("g", (quality.Criterion("citation style", "", 0.1),))},
                                       {"quality_weights": {"concision": 0.7}})
    assert resolved.sources == ("representative", "guidance", "prioritization") and resolved.name == "representative+guidance+prioritization"
    assert [(c.name, c.weight) for c in resolved.criteria] == [("concision", 0.7), ("citation style", 0.1)]
    weighed = quality.resolve_profile(None, None, {"quality_weights": {"safety": 0.4}})
    assert weighed.criterion("safety").weight == 0.4 and weighed.criterion("helpfulness").weight is None and weighed.sources == ("default", "prioritization")


def test_response_quality_takes_the_resolved_profile_and_judges_only_the_criteria_it_has_an_arm_for():
    case = {"response": "See https://other.example/x", "evidence": "https://blog.rust-lang.org/"}
    assert hubofhubs.run("response-quality", case) == ["link not in the evidence: https://other.example/x"]
    without = quality.QualityProfile("brief", (quality.Criterion("concision", "short"),))
    assert hubofhubs.run("response-quality", dict(case, profile=without)) == []        # no criterion it can judge: nothing to report
    with_it = quality.resolve_profile(None, None, {"quality_weights": {"faithfulness to evidence": 1.0}})
    assert hubofhubs.run("response-quality", dict(case, profile=with_it))


def test_critical_thinking_resolves_the_profile_and_reports_goal_and_quality_steps():
    arm = hubofhubs.resolve("think-critically", "composition")
    from hubofhubs.critique.evidence_check import EvidenceCheck

    part = arm(Absent(), Absent(), Absent(), EvidenceCheck())
    result = part.evaluate("q", "See https://other.example/x", {"done_standard": "cited"}, "x", priorities={"quality_weights": {"safety": 0.4}})
    assert result["profile"] == "default+prioritization"
    assert [(s["solution"], s["status"]) for s in result["steps"]] == [("goal-completion", "pending"), ("response-quality", "done")]
    assert result["findings"] == ["link not in the evidence: https://other.example/x"]
