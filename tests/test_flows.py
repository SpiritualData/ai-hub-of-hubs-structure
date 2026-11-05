"""The flow of the hub, run for real over fakes: every container's composition calls the entry point of each solution it uses, a solution with no arm
yet comes back as a pending step with its reason (never as made-up output), and the quality profile is resolved before Response Quality judges."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hubofhubs  # noqa: E402
from esoi import Pending  # noqa: E402
from hubofhubs.the_consciousness.representatives import quality  # noqa: E402
from hubofhubs.the_intelligence.nervous_system.signals import RiskSignal  # noqa: E402
from hubofhubs.the_self.steps import NO_ARM  # noqa: E402
from test_oneline import FakeProvider, whole_hub  # noqa: E402

NO_ARM_SOLUTIONS = ("feedback-learning", "esoi-application", "long-term-memory", "live-objectives", "guidance",
                    "the-intuition", "role-understanding", "the-hands")


def walk(steps):
    for step in steps:
        yield step
        yield from walk(step.get("steps", ()))


def test_the_self_responds_through_every_container_and_reports_what_has_no_arm(tmp_path):
    result = hubofhubs.run("hub-of-hubs", "what is the latest Rust version?", **whole_hub(tmp_path))
    assert "1.90.0" in result.answer and "https://blog.rust-lang.org/" in result.answer      # what the Response Writer wrote from the delegated search
    top = [(s["solution"], s["status"]) for s in result.steps]
    assert top == [("the-consciousness", "done"), ("the-body", "done"), ("the-intelligence", "done"), ("role-understanding", "pending"), ("the-body", "done"),
                   ("system-integrity", "done"), ("the-consciousness", "done")]
    assert result.steps[-1]["steps"] == [{"solution": "feedback-learning", "status": "skipped", "reason": "no feedback was given"}]   # nothing to learn from
    every = {s["solution"]: s for s in walk(result.steps)}
    for sid in ("planner", "delegation", "response-writer", "context-intake", "higher-mind", "metric-translation", "goal-completion"):
        assert every[sid]["status"] == "done", (sid, every[sid])
    for sid in ("long-term-memory", "live-objectives", "guidance", "the-hands", "esoi-application"):
        assert every[sid]["status"] == "pending" and every[sid]["reason"] == NO_ARM, (sid, every[sid])
    assert result.note == "" and result.items[0]["url"].startswith("https://blog.rust-lang.org/")
    assert result.to_dict()["steps"] == list(result.steps)


def test_without_a_key_a_question_that_needs_the_web_reports_the_failed_piece_and_makes_no_answer_up():
    result = hubofhubs.run("hub-of-hubs", "what is the latest Rust version?", environ={})
    assert "failed" in result.answer and "no Gemini API key" in result.answer and "1.9" not in result.answer      # the writer says the step failed; nothing is invented
    assert result.note == "stopped for budget: ask human"      # the failure is never "met": the replan loop spent its budget and Judgment Calls was asked


def test_the_run_is_recorded_in_the_run_store_and_never_in_the_cards(tmp_path):
    store = hubofhubs.run(hubofhubs.the_body.internal_context.card_store.interface.CardStore)
    keywords = whole_hub(tmp_path, provided={"vendor-model-caller": FakeProvider(), "card-store": store})
    system = hubofhubs.assemble(**keywords)
    result = system["the-self"].respond("what is the latest Rust version?")
    assert store.count() == 0                                         # a run is not knowledge: recall can never return it
    runs = system["internal-context"].runs_so_far()
    assert len(runs) == 1 and runs[0]["request"] == "what is the latest Rust version?" and runs[0]["answer"] == result.answer
    audit = hubofhubs.resolve("system-integrity", "prompts_as_data")
    assert audit.audit_run(audit, {"answer": "x", "steps": [{"solution": "a", "status": "pending"}]}) == [
        "step a is pending and does not say why", "an answer was given but the Response Writer did not run"]
    assert result.note == ""


@pytest.mark.parametrize("sid", NO_ARM_SOLUTIONS)
def test_a_solution_with_no_arm_has_its_interface_and_says_no_arm_yet(sid):
    with pytest.raises(Pending) as raised:
        hubofhubs.run(sid, environ={})
    assert {r.kind for r in raised.value.reasons} == {"provided"} and "no arm yet" in str(raised.value)


class Planner:
    def plan(self, request, context=None, target=None, guidance=None, unmet=None):
        return [{"piece": "read the file", "sub_goal": "file read"}, {"piece": "delete the old backup folder", "sub_goal": "folder gone"}]


class Delegation:
    def __init__(self):
        self.handed = []

    def delegate(self, pieces, authority=None, budget=None, cancelled=None, context=None):
        self.handed.append((list(pieces), authority))
        return [{"piece": p["piece"], "result": "done"} for p in pieces]


class Writer:
    def write(self, results, profile=None):
        return "; ".join(r["piece"] for r in results)


class Intake:
    def take(self, request, prepared=None, outside=None, instructions=None):
        return {"view": request}


class Watch:
    def digest(self, **fields):
        return fields["plan_goal"]

    def oversee(self, provider, model, digest):
        raise NotImplementedError

    def watch(self, digest, model=""):
        return RiskSignal("high" if "delete" in digest else "none", "a deletion" if "delete" in digest else "")


class Judgment:
    def decide(self, signal, person="", context=None):
        return {"decision": "decline" if signal["severity"] == "high" else "proceed"}


def test_the_mind_checks_the_risk_signal_and_the_persons_decision_before_it_delegates():
    delegation = Delegation()
    provided = {"planner": Planner(), "delegation": delegation, "response-writer": Writer(), "context-intake": Intake(), "nervous-system": Watch(),
                "judgment-calls": Judgment()}
    out = hubofhubs.run("the-mind", {"request": "tidy up", "authority": {"person": "p1"}}, provided=provided, environ={})
    assert delegation.handed == [([{"piece": "read the file", "sub_goal": "file read"}], {"person": "p1"})]    # the risky piece was declined for this person
    assert out["text"] == "read the file; delete the old backup folder"        # the writer is told the declined piece was not done
    assert out["results"][-1]["refused"] == "asked"
    order = [(s["solution"], s["status"]) for s in out["steps"]]
    assert order[0] == ("context-intake", "done") and order[1] == ("planner", "done") and order[-2:] == [("delegation", "done"), ("response-writer", "done")]
    assert [s for s, _ in order].count("judgment-calls") == 2


class Absent:
    """A seat that has no arm: reading any method of it fails the way an unbuilt seat does."""
    def __getattr__(self, name):
        from esoi import AssemblyError
        raise AssemblyError("no arm yet for this seat")


def test_a_piece_whose_risk_cannot_be_checked_is_not_handed_on():
    delegation = Delegation()
    mind = hubofhubs.resolve("the-mind", "composition")(Intake(), Planner(), delegation, Writer(), Absent(), Judgment())
    out = mind.think("tidy up")
    assert delegation.handed == [([], {})]
    assert [s["status"] for s in out["steps"] if s["solution"] == "nervous-system"] == ["pending", "pending"]


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
    arm = hubofhubs.resolve("critical-thinking", "composition")
    from hubofhubs.the_intelligence.critical_thinking.response_quality.evidence_check import EvidenceCheck

    part = arm(Absent(), Absent(), Absent(), EvidenceCheck())
    result = part.evaluate("q", "See https://other.example/x", {"done_standard": "cited"}, "x", priorities={"quality_weights": {"safety": 0.4}})
    assert result["profile"] == "default+prioritization"
    assert [(s["solution"], s["status"]) for s in result["steps"]] == [("goal-completion", "pending"), ("response-quality", "done")]      # a pending check is reported, never faked
    assert result["findings"] == ["link not in the evidence: https://other.example/x"]


class Critical:
    """Critical Thinking that says the goal is met from the given attempt on (never when ``met_on`` is 0)."""
    def __init__(self, met_on):
        self.met_on, self.checked = met_on, 0

    def translate(self, request, parent=None):
        return {"target": {"done_standard": "done", "budget": {"attempts": 3}}, "steps": []}

    def evaluate(self, request, response="", target=None, evidence="", representative=None, guidance=None, priorities=None, outcome=None):
        self.checked += 1
        met = bool(self.met_on) and self.checked >= self.met_on
        return {"profile": "default", "goal": {"met": met, "reason": "" if met else "the piece failed"}, "findings": [], "steps": []}


class Thinker:
    def __init__(self, refused=""):
        self.calls, self.refused = [], refused

    def think(self, request, authority=None, target=None, guidance=None, profile=None, prepared=None, unmet=None, outside=None, budget=None, cancelled=None):
        self.calls.append((unmet, outside))
        return {"text": "t", "results": [{"piece": "p1", "met": False, "items": [{"url": "https://e.org/a"}], "text": "partial", **({"refused": self.refused} if self.refused else {})}],
                "steps": []}


class Quiet:
    def view(self, request, person=""):
        return {"objectives": [], "guidance": None, "steps": []}

    def prepare(self, request, files=None, budget_tokens=4000):
        return {"cards": []}

    def decide(self, signal, person="", context=None):
        return {"decision": "ask", "to": "human", "context": context}


def intelligence(critical, thinker):
    from hubofhubs.the_intelligence.flow import IntelligenceComposition
    return IntelligenceComposition(Quiet(), Quiet(), critical, thinker, Quiet(), Absent(), Absent())


def test_an_unmet_goal_returns_to_the_planner_within_the_budget():
    thinker, critical = Thinker(), Critical(met_on=2)
    out = intelligence(critical, thinker).process("do it", representative={"person": "p1"})
    assert len(thinker.calls) == 2 and out["attempts"] == 2 and out["stopped"] == "" and out["escalation"] is None
    assert thinker.calls[0] == (None, None)
    assert thinker.calls[1][0] == {"failed_pieces": ["p1"], "reason": "the piece failed"}       # the Planner is told what failed
    assert thinker.calls[1][1]["items"] == [{"url": "https://e.org/a"}]                          # and Context Intake takes in what the workers brought


def test_when_the_budget_runs_out_the_flow_goes_to_judgment_calls():
    thinker = Thinker()
    out = intelligence(Critical(met_on=0), thinker).process("do it", representative={"person": "p1"})
    assert len(thinker.calls) == 3 and out["stopped"] == "budget" and out["escalation"]["context"] == {"stopped": "budget"}


def test_when_authority_runs_out_the_flow_stops_at_once_and_asks():
    thinker = Thinker(refused="authority")
    out = intelligence(Critical(met_on=0), thinker).process("do it")
    assert len(thinker.calls) == 1 and out["stopped"] == "authority" and out["escalation"]["decision"] == "ask"


def test_a_cancel_stops_the_flow_without_asking_anyone():
    thinker = Thinker(refused="cancelled")
    out = intelligence(Critical(met_on=0), thinker).process("do it")
    assert len(thinker.calls) == 1 and out["stopped"] == "cancelled" and out["escalation"] is None


def test_feedback_is_applied_by_esoi_application_with_no_approval_unless_judgment_calls_asks():
    from hubofhubs.the_consciousness.flow import ConsciousnessComposition

    class Feedback:
        def learn(self, person="", feedback=None):
            return {"edit": "tighten concision weight"}

    class Esoi:
        def __init__(self):
            self.applied = []

        def apply(self, change):
            self.applied.append(change)
            return {"applied": True}

    class Proceed:
        def decide(self, signal, person="", context=None):
            return {"decision": "proceed"}

    esoi = Esoi()
    flow = ConsciousnessComposition(Absent(), Absent(), Proceed(), Feedback(), esoi, Absent())
    out = flow.learn("p1", {"text": "too long"})
    assert esoi.applied == [{"edit": "tighten concision weight"}] and out["steps"][-1]["status"] == "done"
    asking = ConsciousnessComposition(Absent(), Absent(), Quiet(), Feedback(), Esoi(), Absent())
    held = asking.learn("p1", {"text": "too long"})
    assert held["decision"]["decision"] == "ask" and held["steps"][-1]["status"] == "skipped"


def test_a_failed_worker_is_never_met_and_a_refused_one_is_not_either():
    failed = hubofhubs.run("goal-completion", {"goal": "g", "done_standard": "a cited answer", "outcome": {"text": "it failed: SearchBackendError", "error": "SearchBackendError: down"}})
    assert failed["met"] is False and "failed" in failed["reason"]
    assert hubofhubs.run("goal-completion", {"goal": "g", "done_standard": "x", "outcome": {"text": "ok", "refused": "authority"}})["met"] is False
    nonempty = hubofhubs.resolve("goal-completion", "nonempty")()
    assert nonempty.check("g", "x", {"text": "it failed", "error": "boom"})["met"] is False


def test_a_piece_nobody_decided_on_is_not_handed_on_and_a_missing_judgment_is_never_proceed():
    delegation = Delegation()
    mind = hubofhubs.resolve("the-mind", "composition")(Intake(), Planner(), delegation, Writer(), Watch(), Absent())
    out = mind.think("tidy up")
    assert delegation.handed == [([], {})]
    assert [r["refused"] for r in out["results"] if r.get("refused")] == ["no decision could be made", "no decision could be made"]


def test_an_unsure_step_is_medium_and_the_default_person_is_asked_about_it():
    signal = hubofhubs.run("nervous-system", "Run the tidy script")
    assert signal.severity == "medium"
    assert hubofhubs.run("judgment-calls", {"signal": {"reason": "no severity named"}, "person": ""})["decision"] == "ask"      # no severity is never none


# --- an autopilot built on Proactivity and Prioritization: what is due, and what matters first -------------------------------------------------------------------

SCHEDULES = [
    {"name": "weekly-report", "request": "write the weekly report", "cadence": "weekly", "kind": "standing-work", "horizon": "week"},
    {"name": "daily-review", "request": "do the daily review", "cadence": "daily", "kind": "standing-work", "horizon": "today"},
    {"name": "done-today", "request": "already ran", "cadence": "daily", "last_run": "2026-07-12T08:00:00Z"},
    {"name": "on-event", "request": "react to the event", "reactive": False, "event_source": "quest-events", "last_run": "2026-07-01T00:00:00Z", "horizon": "month"},
]
NOW = "2026-07-12T09:00:00Z"


def test_the_unasked_work_comes_back_due_and_most_important_first_through_the_whole_flow(tmp_path):
    system = hubofhubs.assemble(**whole_hub(tmp_path))
    out = system["the-intelligence"].proactive(
        SCHEDULES, NOW, person="p", candidates=[{"id": "open-ask", "kind": "ask", "request": "answer the ask", "asked_at": "2026-07-10T09:00:00Z"}],
        events=[{"source": "quest-events", "at": "2026-07-05T00:00:00Z"}])
    assert [t["schedule"] for t in out] == ["open-ask", "daily-review", "weekly-report", "on-event"]      # the ask, then the horizons shortest first
    assert [t["rank"] for t in out] == [1, 2, 3, 4] and all(t["priority_reason"] and t["metric"]["milestone"] for t in out)
    assert [t["kind"] for t in out] == ["waiting", "period", "period", "event"]      # what each was due for; the pulled event made the reactive schedule due
    assert sum(t["metric"]["weight"] for t in out) == pytest.approx(1.0, abs=1e-3)


def test_what_the_person_deferred_is_held_back_and_their_order_wins(tmp_path):
    system = hubofhubs.assemble(**whole_hub(tmp_path))
    out = system["the-intelligence"].proactive(SCHEDULES, NOW, person="p", stated={"order": ["weekly-report"], "not_before": {"daily-review": "2026-07-13T00:00:00Z"}})
    assert [t["schedule"] for t in out] == ["weekly-report"]


def test_the_self_acts_unasked_in_the_order_prioritization_gives(tmp_path):
    system = hubofhubs.assemble(**whole_hub(tmp_path))
    asked = []
    system["the-self"].respond = lambda request, person="", **kw: asked.append(request) or request
    out = system["the-self"].act_unasked(SCHEDULES[:2], NOW, person="p")
    assert asked == ["do the daily review", "write the weekly report"] and out == asked


def test_without_prioritization_the_due_order_stays_and_no_work_is_made_up():
    from hubofhubs.the_intelligence.flow import IntelligenceComposition
    from hubofhubs.the_intelligence.proactivity.triggers import CalendarAndEvents
    part = IntelligenceComposition(Absent(), Absent(), Absent(), Absent(), Absent(), CalendarAndEvents(), Absent())
    assert [t["schedule"] for t in part.proactive(SCHEDULES[:2], NOW)] == ["weekly-report", "daily-review"]
