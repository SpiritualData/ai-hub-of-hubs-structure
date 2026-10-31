"""The overseer mixin on a stand-in host: gate, digest fields, degraded fallback, collect and the late follow-up."""
import threading
import time
from concurrent.futures import Future
from types import SimpleNamespace as NS

from hubofhubs.orchestrate.oversee import OverseeMixin
from hubofhubs.orchestrate.plan import PlanDecision
from hubofhubs.ports.deep import ProgressEvent
from hubofhubs.ports.events import EVENT_OVERSEER
from hubofhubs.risk import OverseerSignal

CFG = NS(max_steps=10, max_elapsed_seconds=90.0, max_gathered_chars=1000, planner_tier="p", overseer_tier="o",
         overseer_digest_char_budget=500, overseer_gate_min_consecutive_reads=2, overseer_gate_repeat_plan=True,
         overseer_gate_spend_fraction=0.6, overseer_background_finish_timeout_seconds=2.0)


class Registry:
    def resolve_tier(self, name):
        return {"o": "model-o", "p": "model-p"}[name]


class Host(OverseeMixin):
    def __init__(self, signals=None):
        self.cfg, self.registry, self.provider, self.escalation = CFG, Registry(), NS(tokens_in=3, tokens_out=4), object()
        self.signals, self.digests, self.late, self.consults = signals or {}, [], [], []

    def get_provider_for_model(self, model):
        return f"provider-{model}"

    def oversee_summarize_observation(self, observation):
        return str(observation.get("text"))

    def oversee_digest(self, **fields):
        self.digests.append(fields)
        return "digest"

    def oversee_consult(self, provider, model, digest):
        self.consults.append(model)
        return self.signals.get(model, OverseerSignal("proceed"))

    def oversee_escalate_late(self, reason, scope_id):
        self.late.append((reason, scope_id))


class Inline:
    def submit(self, fn):
        future = Future()
        future.set_result(fn())
        return future


READS = [{"kind": "read", "text": "abc"}, {"kind": "grep", "text": "de", "hits": [1]}]


def test_spend_metrics_and_operation_lines():
    chars, reads, elapsed = Host().spend_metrics(READS, 0.0)
    assert chars == 3 + 2 + len("[1]") and reads == 2 and elapsed >= 0
    assert Host().operation_lines(READS + ["junk"], window=1) == (["[grep] de"], 2)


def test_a_calm_step_is_gated_out_and_a_stuck_read_loop_is_consulted():
    host = Host()
    assert host.submit_oversee(Inline(), user_message="q", step=1, plan=None, gathered=[], started=time.monotonic()) is None
    pending = host.submit_oversee(Inline(), user_message="q", step=1, plan=PlanDecision(action="read"), gathered=READS, started=0.0)
    assert pending["step"] == 1 and host.consults == ["model-o"]
    fields = host.digests[0]
    assert fields["tokens_in"] == 3 and fields["plan_action"] == "read" and fields["char_budget"] == 500


def test_a_degraded_consult_retries_once_at_the_planner_tier():
    host = Host({"model-o": OverseerSignal("proceed", degraded=True), "model-p": OverseerSignal("redirect", hint="h")})
    pending = host.submit_oversee(Inline(), user_message="q", step=1, plan=None, gathered=READS, started=0.0, gate=False)
    assert host.consults == ["model-o", "model-p"] and pending["future"].result().signal == "redirect"


def test_collect_records_the_signal_and_emits_once_resolved():
    host, signals, events = Host(), [], []
    emit = NS(emit=events.append)
    pending = {"future": Future(), "step": 2, "plan": PlanDecision(action="read")}
    assert host.collect_oversee(pending, signals=signals, emit=emit) is None
    pending["future"].set_result(OverseerSignal("redirect", hint="h", reason="r"))
    got = host.collect_oversee(pending, signals=signals, emit=emit)
    assert got.signal == "redirect" and signals == [{"signal": "redirect", "hint": "h", "reason": "r", "step": 2}]
    assert events[0].type == EVENT_OVERSEER and events[0].action == "read"
    assert host.collect_oversee(None, signals=signals, emit=None) is None


def run_late(host, signal, **kw):
    future, events, done = Future(), [], threading.Event()
    future.set_result(signal)
    emit = NS(emit=lambda e: (events.append(e), done.set()))
    host.finish_oversee_in_background({"future": future, "step": 1, "plan": None}, emit=emit, scope_id="s1", **kw)
    done.wait(2)
    return events


def test_a_late_human_escalation_is_raised_unless_a_brainstorm_is_active():
    host = Host()
    events = run_late(host, OverseerSignal("escalate_human", reason="why"))
    threading.Event().wait(0.1)
    assert events[0].data["late"] is True and host.late == [("why", "s1")]
    quiet = Host()
    run_late(quiet, OverseerSignal("escalate_human", reason="why"), brainstorm_active=True)
    threading.Event().wait(0.1)
    assert quiet.late == []
