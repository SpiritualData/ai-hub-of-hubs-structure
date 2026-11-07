"""Rebuild cases.json for Route a Request from invented requests whose route is known, three kinds of the failures this seat exists to end plus plain cases of each route:
a status question that must not start work, a count question that must be answered from a read, a bare cue that names a tracked milestone and so asks to move it, and a draft
that must be written in the reply rather than handed to a background run.

    python3 evaluation/route_a_request/build_cases.py

A case is a request (and optionally the view the Mind already has); ``expect`` is the route. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MILESTONES = "Milestones on this quest: newsletter subscribers; podcast listeners; workshop signups."

INFORMATION = [
    "Where do we stand on the newsletter subscribers milestone?", "How many goals are open this week?", "What is the status of the workshop signups?",
    "Which of my goals is due first?", "Who owns the podcast milestone?", "What did we decide about the launch date last week?",
    "How is the checkout page doing since Monday?", "Remind me what the done-when is for the listeners milestone.", "Is the invoice from March paid?",
    "Why did the signup count drop on Tuesday?", "What does the weekly review step involve?", "Can you tell me how many people replied to the survey?",
]
ACT = [
    "Add a goal for this week: send the spring survey to the list.", "Mark the workshop outline goal as done.", "Move the launch call to Thursday afternoon.",
    "Create a note on the podcast quest saying the guest confirmed.", "Assign the invoice follow-up to Dana.", "Start a research run on competitor pricing and report back when done.",
    "Update the checkout page copy in the repository and open a change for it.", "Schedule a reminder for Friday to renew the domain.",
    "Push the workshop signups milestone forward this week.", "Send the agenda to the team before the call.",
]
CUES = [("newsletter subscribers", "act"), ("podcast listeners", "act"), ("workshop signups", "act")]
DRAFT = [
    "Write a short caption for the launch photo.", "Draft two versions of the subject line for Friday's email.", "Give me a three sentence description of the workshop for the website.",
    "Compose a thank you note to the guest, I will send it myself.", "Write the opening paragraph of the newsletter.", "Can you word a post announcing the new episode?",
    "Draft the message I could send to the volunteers about Saturday.", "Put together a short agenda for the call as text here.",
]
CLARIFY = [
    "Do the thing from before.", "Update it.", "Send that to them.", "Make it better.", "and also the other one", "Move it to next week.",
    "Fix the numbers.", "Can you look at the one Dana mentioned?",
]


def case(prefix, index, request, route, view=""):
    return {"id": f"route-{prefix}-{index:02d}", "kind": route, "args": {"request": request, "context": {"view": view} if view else {}}, "expect": route}


def main():
    cases = []
    for i, text in enumerate(INFORMATION, 1):
        cases.append(case("information", i, text, "information", MILESTONES))
    for i, text in enumerate(ACT, 1):
        cases.append(case("act", i, text, "act", MILESTONES))
    for i, (text, route) in enumerate(CUES, 1):
        cases.append(case("cue", i, text, route, MILESTONES))
    for i, text in enumerate(DRAFT, 1):
        cases.append(case("draft", i, text, "draft"))
    for i, text in enumerate(CLARIFY, 1):
        cases.append(case("clarify", i, text, "clarify"))
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
