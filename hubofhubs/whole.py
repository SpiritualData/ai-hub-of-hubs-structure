"""The Assembler and The Self. The Assembler (``assemble-the-whole``) answers free text from what is remembered and from the outside world,
holds the answer to its evidence and reports whether the hub stays generic. The Self (``the-self``) responds to a request as the whole: its
flow, ``respond``, runs Consciousness, Body and Intelligence in order and reports every part, then the Assembler gives the answer the existing
arms can give until the Response Writer has an arm."""
import time
from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional

from esoi import implementation
from esoi.assemble import Lazy

from .oneline import Result, event, trace_event
from .ports.events import EVENT_DONE, EVENT_RESULT, EVENT_STATUS, EVENT_WORK_TRACE
from . import steps
from .seats import (ContextRetrieval, FormAndContext, Genericity, HumanAdapting, InformationProcessing, ModelPlumbing, Remembering,
                    ResponseJudging, TakingIn, WholeAnswering)
from .steps import DONE, Step, listing, skipped, take


MODEL_ONLY_NOTE = "answered from the model only: no sources were consulted"


@implementation("assemble-the-whole", "zero_config")
class ZeroConfig:
    """Every seat from its selected arm: what is remembered and what the web says answer the text, and the response judge holds the answer to
    its sources. The answer path needs the world, recall and the judge; the model, the audit and the file retrieval are built on first use,
    so a question never asks for what only they need."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, take_in: TakingIn, recall: Remembering, critic: ResponseJudging, model: Lazy[ModelPlumbing],
                 generic: Lazy[Genericity], retrieval: Lazy[ContextRetrieval]):
        self.take_in, self.recall, self.critic = take_in, recall, critic
        self.model, self.generic = model, generic
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
        findings = self.critic.judge(answer, evidence)
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
        text = self.model.ask(prompt, tier)
        done = [event(EVENT_STATUS, "asking the model; answered from the model only: no sources were consulted"),
                event(EVENT_RESULT, text, result_kind="answer"), event(EVENT_DONE, "", result_kind="answer", seat="model-plumbing")]
        return Result(input=prompt, seat="model-plumbing", answer=text, arms={"model-plumbing": type(self.model).__name__},
                      seconds=time.monotonic() - began, note=MODEL_ONLY_NOTE, events=tuple(done))

    def context_for(self, task: str, files: Mapping[str, str], budget_tokens: int = 4000) -> List[Any]:
        """The pieces of ``files`` (path to text) that ``task`` needs within a token budget, by the selected retrieval arm; an empty list
        means the task needs no context from them."""
        return list(self.retrieval.retrieve(task, files, budget_tokens))

    def health(self) -> Mapping[str, Any]:
        """Whether the hub stays generic and current: the audit of the generic seat for no vendor terms."""
        return self.generic.audit(())


@implementation("the-self", "composition")
class SelfComposition:
    """The Self responds as the whole. Its flow, in order: Consciousness represents the person, Body describes where the system's data lives,
    Intelligence processes the request with the Representative's authority, and then, because the Response Writer has no arm yet, the Assembler
    gives the answer the existing arms can (what is remembered and what the web says, held to its evidence); Consciousness learns from feedback
    when there is some. The result lists the step of every part and says which have no arm yet. The other operations are the Assembler's, and
    ``take_in`` reaches the outside through World. The seats of Body, Intelligence and Consciousness are built on first use."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, whole: WholeAnswering, world: TakingIn, body: Lazy[FormAndContext], intelligence: Lazy[InformationProcessing],
                 consciousness: Lazy[HumanAdapting]):
        self.whole, self.world = whole, world
        self.body, self.intelligence, self.consciousness = body, intelligence, consciousness

    def respond(self, request: str, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Result:
        known = take(self.consciousness, "the-consciousness", person=person)
        context = take(self.body, "the-body", person=person)
        who = (known.output or {}) if known.status == DONE else {}
        processed = take(self.intelligence, "the-intelligence", request=request, person=person, representative=who.get("representative"),
                         priorities=who.get("priorities"))
        log = [known, context, processed]
        result = self.whole.answer(request)
        log.append(Step("assemble-the-whole", DONE, reason="interim answer from the existing arms until the Response Writer has an arm"))
        text = (processed.output or {}).get("answer", "") if processed.status == DONE else ""
        if text:
            result = replace(result, answer=text)
        log.append(take(self.consciousness, "the-consciousness", method="learn", person=person, feedback=feedback))
        return replace(result, steps=tuple(listing(log)))

    def answer(self, text: str) -> Result:
        return self.whole.answer(text)

    def model_only(self, prompt: str, tier: str = "") -> Result:
        return self.whole.model_only(prompt, tier)

    def context_for(self, task: str, files: Mapping[str, str], budget_tokens: int = 4000) -> List[Any]:
        return self.whole.context_for(task, files, budget_tokens)

    def health(self) -> Mapping[str, Any]:
        return self.whole.health()

    def take_in(self, query: str, scholarly: bool = False) -> Mapping[str, Any]:
        """What the outside world says for ``query``, through World (a web search and, with ``scholarly=True``, papers)."""
        return self.world.take_in(query, scholarly)
