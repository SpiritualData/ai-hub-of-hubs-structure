# Build an autopilot on the hub

An autopilot is a loop that wakes up, asks what is due, picks what matters first and does it, without anyone asking. The hub gives you the two parts
that decide this, so you write only the loop and your own sources.

- **Proactivity** says what is due: standing schedules by calendar period in their own time zone, a run someone requested, or an event since the last run.
- **Prioritization** says what matters first among that work and the other work waiting (open asks, standing work, ideas), for this person. It is also the one part that
  orders the asks you put to the person and the person's own goals, shown below.

The autopilot is the consumer. The hub holds no consumer words, prompts or settings: you hand it your schedules, your waiting work and your event source.

## What each part takes and returns

A **schedule** is a mapping with `name`, `request`, `cadence` (`daily`, `weekly` or `monthly`), `zone` (an IANA zone), `last_run`, `run_requested_at` and, for
a reactive one, `event_source`. Proactivity returns one **trigger** for each schedule that is due: `schedule`, `kind` (`requested`, `event`, `period` or
`elapsed`, the names in `TRIGGER_KINDS`), `reason` and the `request` to run.

A **candidate** is anything that competes for attention: `id`, `kind` (`ask`, `standing-work` or your own) and the fields your data
carries (`CANDIDATE_FIELDS`: the person's own rank, deadline, who is waiting, what blocks it, when it was asked, when the person was last nudged). What the
person said is a `Stated`: an explicit `order`, what to `deferred`, `not_before`, `only_kinds`, `feedback` that implies sooner or later, and
`quality_weights`. Keep it in the Representative's `preferences["priorities"]` and `act_unasked` reads it from there.

The ordered answer lists each item with its `rank`, the `reason` in words and a `metric` (milestone, weight, due, criterion) that Metric Translation and the
Planner use; what the person's constraints hold back is listed apart with why. Nothing is guessed: a field a candidate does not carry is skipped.

## Your event source goes through Intake Sources

Declare your system's events as an Intake Sources adapter (`IntakeSourcing`: `sources()` and `pull(source, limit)`). Each pulled item carries `source` and
`at`. A schedule that names the same `event_source` becomes reactive, and `attach_events` adds the pulled times to it. Nothing about your events is written
in hub code.

## A runnable loop

This page is run by `tests/test_autopilot_how_to.py`, so it cannot rot. It needs no key and no network.

```python
from hubofhubs.api import Stated, assemble, attach_events, ordered_ids


class ProductEvents:
    """Your adapter: where this system's events come from (here, one fixed event)."""

    def sources(self):
        return [{"kind": "product-events", "description": "things that happened in the product"}]

    def pull(self, source="", limit=10):
        return [{"text": "an ask was answered", "person": "", "source": "product-events", "at": "2026-07-05T00:00:00Z"}][:limit]


schedules = [
    {"name": "daily-review", "request": "do the daily review", "cadence": "daily", "deadline": "2026-07-12T12:00:00Z"},
    {"name": "weekly-report", "request": "write the weekly report", "cadence": "weekly", "deadline": "2026-07-19T00:00:00Z"},
    {"name": "on-answer", "request": "react to the answered ask", "event_source": "product-events", "last_run": "2026-07-01T00:00:00Z"},
]
waiting = [{"id": "ask-7", "kind": "ask", "request": "send the board the numbers", "asked_at": "2026-07-10T09:00:00Z"}]
now = "2026-07-12T09:00:00Z"

system = assemble(provided={"intake-sources": ProductEvents()})
events = system["intake-sources"].pull("product-events")
print([e["source"] for e in events])

kinds = Stated(kind_order=("ask",)).__dict__      # what the person said: asks first
work = system["the-intelligence"].proactive(schedules, now, person="ana", candidates=waiting, stated=kinds, events=events)
for item in work:
    print(item["rank"], item["schedule"], item["kind"], "|", item["priority_reason"])

stated = Stated(kind_order=("ask",), not_before={"weekly-report": "2026-07-13T00:00:00Z"}).__dict__
later = system["the-intelligence"].proactive(schedules, now, person="ana", candidates=waiting, stated=stated, events=events)
print(ordered_ids([{"id": t["schedule"]} for t in later]))
print(len(attach_events(schedules, events)[2]["events"]))
```

It prints the source of the pulled event, then the work in order (the open ask first because the person's kind order puts asks first, then the schedules by nearest deadline, the reactive schedule last), then the
order when the person said the weekly report must wait (it is held back), then the number of events attached.

To run the work too, call `system["the-self"].act_unasked(schedules, now, person="ana", candidates=waiting, events=events)`: it responds to each trigger, in
this order, as a request through the whole hub (that needs a model key, see the tutorial).

## The asks you put to the person, and the person's goals

Prioritization orders three things, named by `subject`: the work you start unasked (`work`, the default), the asks you put to the person (`asks`) and the person's
goals (`goals`). A person's attention is scarce, so for asks Judgment Calls first decides which are worth asking, and Prioritization then orders them by what answering
each one unblocks, its deadline, its effort and what the person stated, and with a `batch_limit` puts only that many in front of the person and holds the rest, each with
its place and why. A goal is a solution milestone as the ESOI specification defines it: a priority of one solution of an intent, with a target time, dependencies on other
milestones and what reaching it unblocks. A milestone may have no metric value; it is ordered by the same fields. A milestone that is met, or whose end condition has
passed, is held back. What the person said about a milestone's solution or intent counts for its milestones.

```python
asks = [
    {"id": "colour", "severity": "medium", "reason": "pick a colour"},
    {"id": "plan", "severity": "medium", "reason": "approve the plan", "unblocks": ["draft", "review"], "deadline": "2026-07-13T00:00:00Z"},
    {"id": "typo", "severity": "none"},
    {"id": "name", "severity": "medium", "reason": "pick a name", "unblocks": ["draft"]},
]
put = system["the-consciousness"].order_asks(asks, "ana", batch_limit=2, now=now)
print([a["id"] for a in put["asks"]], [h["id"] for h in put["held"]], [n["id"] for n in put["not_asked"]])

milestones = [
    {"id": "ship", "kind": "milestone", "solution": "reader", "intent": "launch", "deadline": "2026-08-01T00:00:00Z", "blocked_by": ["build"], "metric": 0.9},
    {"id": "build", "kind": "milestone", "solution": "reader", "intent": "launch", "deadline": "2026-07-20T00:00:00Z"},
    {"id": "polish", "kind": "milestone", "solution": "style", "intent": "launch", "deadline": "2026-07-25T00:00:00Z"},
    {"id": "survey", "kind": "milestone", "solution": "style", "intent": "launch", "met": "2026-06-01T00:00:00Z"},
]
goals = system["prioritization"].prioritize(candidates=milestones, subject="goals", stated={"feedback": [{"about": "style", "direction": "later"}]}, now=now)
print(ordered_ids(goals["ordered"]), [h["id"] for h in goals["held"]])
```

It prints the two asks put in front of the person (the plan that unblocks two items and is due first, then the name that unblocks one), the ask held for a later batch, and
the ask Judgment Calls decided needs no asking; then the milestones in order (`build` unblocks `ship` and is due first, `polish` waits because the person's feedback implies
later for its solution, `ship` follows its dependency) with the met `survey` held back. Judgment Calls decides whether to ask and Prioritization decides the order and the
batch. `Objectives` and Higher Mind read the order of the milestones the same way, through `system["higher-mind"].view(request, person, objectives=...)`.

## What your system adds

- Your schedules and the fields of your waiting work, mapped from your own data. Nothing else needs a hub change.
- Your event source, as one Intake Sources adapter.
- The decision whether the work may be done unasked stays with Judgment Calls and the Nervous System, not with these two parts.
- To change how work is ordered, add an arm of Prioritization and let the metric (`esoi run prioritization`) choose it.
