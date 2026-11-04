"""The composition arm of ``assemble-the-whole``: free text is answered from what is remembered and from the outside world, and the
answer is held to its evidence. The same arm acts on a goal behind the risk watch and reports whether the hub stays generic."""
import time
from typing import Any, Dict, List, Mapping

from esoi import implementation
from esoi.assemble import Lazy

from .oneline import Result, event, trace_event
from .ports.events import EVENT_DONE, EVENT_RESULT, EVENT_STATUS, EVENT_WORK_TRACE
from .seats import Acting, ContextRetrieval, Critiquing, Genericity, Reasoning, Remembering, RiskWatching, TakingIn


MODEL_ONLY_NOTE = "answered from the model only: no sources were consulted"


@implementation("assemble-the-whole", "zero_config")
class ZeroConfig:
    """Every seat from its selected arm: what is remembered and what the web says answer the text, the critic holds the answer to
    its sources, and a goal is acted on only when the risk watch lets it through. The answer path needs the world, recall and the critic;
    the model, the risk watch, the acting seat, the audit and the file retrieval are built on first use, so a question never asks for what only they need."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, take_in: TakingIn, recall: Remembering, critic: Critiquing, reason: Lazy[Reasoning], watch: Lazy[RiskWatching],
                 act: Lazy[Acting], generic: Lazy[Genericity], retrieval: Lazy[ContextRetrieval]):
        self.take_in, self.recall, self.critic = take_in, recall, critic
        self.reason, self.watch, self.act_arm, self.generic = reason, watch, act, generic
        self.retrieval = retrieval

    def answer(self, text: str) -> Result:
        began = time.monotonic()
        trace_id = f"run-{int(began * 1000) % 10**9}"
        events = [event(EVENT_STATUS, "assemble-the-whole: starting")]
        events.append(trace_event(trace_id, "take-in-the-world", "sources", "workTrace.search", "running"))
        remembered = list(self.recall.recall(text, 5))
        found = self.take_in.take_in(text)
        items: List[Dict[str, Any]] = [dict(i) for i in found["items"]]
        cards = [{"id": c.id, "text": c.text, **({"source": c.source} if c.source else {}), **({"tags": list(c.tags)} if c.tags else {})}
                 for c in remembered]
        answer = found["answer"] or "\n".join(c["text"] for c in cards)
        events.append(trace_event(trace_id, "take-in-the-world", "sources", "workTrace.search", "done", counts={"found": len(items)},
                                  items=[{"url": i.get("url"), "label": i.get("title"), "kind": "found"} for i in items]))
        evidence = " ".join(f"{i.get('url', '')} {i.get('snippet', '')}" for i in items)
        findings = self.critic.critique(answer, evidence)
        seconds = time.monotonic() - began
        events.append(event(EVENT_RESULT, answer, result_kind="answer"))
        events.append(event(EVENT_DONE, "", result_kind="answer", seat="assemble-the-whole"))
        return Result(input=text, seat="assemble-the-whole", answer=answer, items=tuple(items + cards),
                      trace=tuple(e.data for e in events if e.type == EVENT_WORK_TRACE),
                      arms={"take-in-the-world": type(self.take_in).__name__, "remember-and-recall": type(self.recall).__name__},
                      seconds=seconds, note="; ".join(findings), events=tuple(events))

    def model_only(self, prompt: str, tier: str = "") -> Result:
        """The model's own words at ``tier``, with a note that no source was consulted (a free-text answer is never taken from model
        memory unless this is called)."""
        began = time.monotonic()
        text = self.reason.reason(prompt, tier)
        done = [event(EVENT_STATUS, "asking the model; answered from the model only: no sources were consulted"),
                event(EVENT_RESULT, text, result_kind="answer"), event(EVENT_DONE, "", result_kind="answer", seat="reason-and-answer")]
        return Result(input=prompt, seat="reason-and-answer", answer=text, arms={"reason-and-answer": type(self.reason).__name__},
                      seconds=time.monotonic() - began, note=MODEL_ONLY_NOTE, events=tuple(done))

    def context_for(self, task: str, files: Mapping[str, str], budget_tokens: int = 4000) -> List[Any]:
        """The pieces of ``files`` (path to text) that ``task`` needs within a token budget, by the selected retrieval arm; an empty list
        means the task needs no context from them."""
        return list(self.retrieval.retrieve(task, files, budget_tokens))

    def act(self, goal: str, brief: str = "") -> Any:
        """Carry out ``goal`` with the acting seat when the risk watch lets the step through; otherwise return the signal."""
        signal = self.watch.watch(self.watch.digest(user_message=goal, step=1, max_steps=1, plan_action=goal, plan_goal=goal))
        if getattr(signal, "signal", "proceed") != "proceed":
            return signal
        return self.act_arm.run_goal(goal=goal, brief=brief)

    def health(self) -> Mapping[str, Any]:
        """Whether the hub stays generic and current: the audit of the generic seat for no vendor terms."""
        return self.generic.audit(())
