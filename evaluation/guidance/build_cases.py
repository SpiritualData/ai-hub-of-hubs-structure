"""Rebuild cases.json for Guidance from the decision rule Quest AI Runner's measured long-term guidance states (QAR ``LONG_TERM_GUIDANCE``, esoi solution
guide-toward-the-long-term-goal): write the answer alone when the matter is urgent, the person is upset, they asked you to stop, the topic has nothing to do with
the work or the objective was raised lately; otherwise (progress reported, asking what is next, finishing, idle, or a request that bears on the work) point at one
next target and its current reading. Every case here is invented with neutral objectives (a long run, a draft, a deployment, a language), none copied from a
consumer's data, and tagged ``source: rule`` with the clause it exercises. The expected result is written by hand from the rule, never produced by an arm.

    python3 evaluation/guidance/build_cases.py

Twelve nudge cases and twelve restraint cases, so the share answered correctly is the two-sided mean (a floor that never nudges and a baseline that always nudges
both score half). Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = {"id": "run", "name": "the 10 km race", "next_target": "complete a 15 km long run by 15 November", "reading": "longest run so far 12 km, target 15 km"}
DRAFT = {"id": "draft", "name": "the thesis draft", "next_target": "send chapter 3 to the committee by 20 November", "reading": "pages drafted 74 of 120"}
SHIP = {"id": "ship", "name": "the new release", "next_target": "finish the migration rehearsal by Friday", "reading": "rehearsals passed 2 of 3"}
LANG = {"id": "lang", "name": "the Spanish conversation goal", "next_target": "pass the B1 mock test by 30 November", "reading": "mock test score 61 percent, target 75 percent"}
WEEKLY = {"id": "weekly", "name": "three runs this week", "next_target": "the third run by Sunday", "reading": "runs this week 2 of 3", "in_focus": True}


def focus(objective):
    return dict(objective, in_focus=True)


def recent(objective):
    return dict(objective, nudged_recently=True)


def case(name, kind, request, objectives, expect):
    return {"id": "guidance-" + name, "kind": kind, "source": "rule " + kind, "args": {"request": request, "objectives": objectives}, "expect": expect}


def main():
    nudge = [
        case("progress-report", "nudge-progress", "I just got back from my long run and felt good. Anything I should log?", [RUN, DRAFT], "run"),
        case("thanks", "nudge-closing", "Thanks, that is all I needed today.", [DRAFT], "draft"),
        case("whats-next", "nudge-whats-next", "What should I work on next?", [SHIP, LANG], "ship"),
        case("idle", "nudge-idle", "I did my daily lesson and I am free for a bit. What would be a good use of 20 minutes?", [LANG], "lang"),
        case("goal-in-focus", "nudge-progress", "I did my second run this morning and my legs feel fine.", [RUN, WEEKLY], "weekly"),
        case("related-lookup", "nudge-related", "What did the committee say about chapter 3 last time?", [RUN, DRAFT], "draft"),
        case("related-question", "nudge-related", "How long should the rehearsal take if the migration touches every table?", [DRAFT, SHIP], "ship"),
        case("goodbye-after-other-work", "nudge-closing", "Great, bye for now.", [recent(RUN), SHIP], "ship"),
        case("several-pick-the-focus", "nudge-whats-next", "Where do things stand?", [DRAFT, focus(LANG), SHIP], "lang"),
        case("done-with-task", "nudge-closing", "I am done for the day.", [focus(DRAFT), RUN], "draft"),
        case("related-plan-request", "nudge-related", "Can you plan my mock test practice for the week?", [SHIP, LANG], "lang"),
        case("status-of-long-run", "nudge-progress", "My long run went to 12 km today, how should I recover?", [DRAFT, RUN], "run"),
    ]
    restrain = [
        case("urgent-outage", "restrain-urgent", "The release is down and customers are writing in, what do I check first?", [SHIP], None),
        case("urgent-injury", "restrain-urgent", "I think I hurt my knee on the long run, it is an injury, what do I do right now?", [RUN], None),
        case("due-today", "restrain-urgent", "The committee form is due today and I cannot find the template.", [DRAFT], None),
        case("upset", "restrain-upset", "I am so discouraged, my mock test score went down again.", [LANG], None),
        case("worried", "restrain-upset", "I'm worried I will never finish the chapter in time.", [DRAFT], None),
        case("stop", "restrain-stop", "Please stop reminding me about the race, I know.", [RUN], None),
        case("unrelated-lookup", "restrain-unrelated", "What time does the pharmacy on Main Street close?", [RUN, DRAFT], None),
        case("unrelated-calculation", "restrain-unrelated", "What is 18 percent of 240?", [LANG], None),
        case("unrelated-translation", "restrain-unrelated", "Translate good morning into German.", [SHIP], None),
        case("recently-raised", "restrain-recent", "I finished the second rehearsal, thanks.", [recent(SHIP)], None),
        case("no-objectives", "restrain-none", "Thanks, that is all I needed today.", [], None),
        case("unrelated-topic", "restrain-unrelated", "Suggest a name for my cat, she is grey with white paws.", [RUN, SHIP, LANG], None),
    ]
    (HERE / "cases.json").write_text(json.dumps(nudge + restrain, indent=1) + "\n")
    print(len(nudge) + len(restrain), "cases")


if __name__ == "__main__":
    main()
