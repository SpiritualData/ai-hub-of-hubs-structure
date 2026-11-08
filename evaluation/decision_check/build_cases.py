"""Rebuild cases.json for Decision Check from invented, neutral scenarios.

A ``pick`` case is a draft pick among two or three options, with the evidence slices three views see (the owner's rules only, prior examples only, descriptions only); ``expect`` is the
option the evidence supports, or the empty string when no slice decides (the right result is then an abstain). The families: the draft is right and the views agree; the draft is wrong and the
rules say so; the draft is wrong and the examples say so; a description misleads by a shared word while the rules decide; the evidence decides nothing. A ``reply`` case is a draft reply with
the reads and the executed actions it must agree with and the people present; ``remove`` lists the spans that must be gone from the checked reply and ``keep`` the spans that must stay (the claims
that hold, and a clean reply keeps everything).

    python3 evaluation/decision_check/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES_VIEW = "Pick the option the owner's rules and scopes give for this item. Use only the rules."
EXAMPLES_VIEW = "Pick the option that the prior examples most clearly show for an item like this one. Use only the examples."
DESCRIPTIONS_VIEW = "Pick the option whose description fits this item best. Use only the descriptions."
CLAIMS_VIEW = "A statement that something was read or looked up must be supported by the reads listed in the evidence. Statements about anything else are not this task."
ACTIONS_VIEW = "A statement that an action was done (past tense, as a fact) must be supported by an executed action record in the evidence. A plan or promise, a read, a question or a fact about the world is not this task."
ASKS_VIEW = "A question or request addressed to a named person who is not listed as present in the evidence fails this task. A question to a person who is present, and every statement that is not a question or request, does not fail it."


def pick(name, draft, expect, item, options, rules, examples, descriptions):
    views = [{"id": "rules", "instruction": RULES_VIEW + " Item: " + item, "evidence": rules},
             {"id": "examples", "instruction": EXAMPLES_VIEW + " Item: " + item, "evidence": examples},
             {"id": "descriptions", "instruction": DESCRIPTIONS_VIEW + " Item: " + item, "evidence": descriptions}]
    return {"id": "pick-" + name, "kind": "pick", "args": {"draft": draft, "binding": {"kind": "pick", "options": options, "views": views, "max_calls": 6}}, "expect": expect}


def reply(name, text, reads, actions, present, remove, keep):
    views = [{"id": "claims", "instruction": CLAIMS_VIEW, "evidence": "Reads:\n" + reads},
             {"id": "actions", "instruction": ACTIONS_VIEW, "evidence": "Executed actions:\n" + actions},
             {"id": "asks", "instruction": ASKS_VIEW, "evidence": "Present in this conversation: " + present}]
    return {"id": "reply-" + name, "kind": "reply", "args": {"draft": text, "binding": {"kind": "reply", "views": views, "max_calls": 8}}, "expect": {"remove": remove, "keep": keep}}


GARDEN = [{"id": "g1", "text": "Orchard Planning"}, {"id": "g2", "text": "Greenhouse Repairs"}, {"id": "g3", "text": "Seed Orders"}]
STUDIO = [{"id": "s1", "text": "Podcast Production"}, {"id": "s2", "text": "Newsletter"}]


def main():
    cases = [
        pick("right-all-agree", "g1", "g1", "Prune the apple trees before spring", GARDEN, "Anything about trees or fruit belongs to Orchard Planning.",
             "Plant new pear trees -> Orchard Planning. Prune the plum trees -> Orchard Planning.", "Orchard Planning: trees and fruit. Greenhouse Repairs: glass and heaters. Seed Orders: packets and suppliers."),
        pick("wrong-rules-decide", "g3", "g2", "Replace the cracked glass panel", GARDEN, "Broken glass, heaters and vents belong to Greenhouse Repairs.",
             "Order tomato seeds -> Seed Orders. Fix the vent hinge -> Greenhouse Repairs.", "Seed Orders: packets and suppliers, including panels of seed samples."),
        pick("wrong-examples-decide", "g1", "g3", "Reorder the basil packets from the usual supplier", GARDEN, "No rule covers this item.",
             "Reorder carrot packets from the supplier -> Seed Orders. Reorder lettuce packets -> Seed Orders. Reorder basil packets -> Seed Orders.",
             "Orchard Planning: trees and fruit and herbs of the orchard."),
        pick("description-misleads-rules-decide", "g2", "g2", "Check the heater in the seed room", GARDEN, "Heaters belong to Greenhouse Repairs, wherever they are.",
             "Order seed trays -> Seed Orders.", "Seed Orders: everything about the seed room."),
        pick("nothing-decides-draft-stands", "g1", "g1", "Talk to Sam about the plan", GARDEN, "No rule covers this item.", "No example resembles this item.", "No description mentions a person or a plan."),
        pick("views-split-nothing-decides", "g2", "", "Sort out the shed", GARDEN, "No rule covers this item.", "Clean the shed floor -> Seed Orders. Clean the shed roof -> Orchard Planning.", "No description mentions a shed."),
        pick("right-despite-misleading-example", "s2", "s2", "Write the monthly subscriber letter", STUDIO, "Anything sent to subscribers belongs to Newsletter.",
             "Record the guest interview -> Podcast Production. Write the monthly recap -> Podcast Production.", "Podcast Production: recording, editing and show notes. Newsletter: letters to subscribers."),
        pick("wrong-rules-and-examples-agree", "s2", "s1", "Cut the silence from episode 4", STUDIO, "Editing audio belongs to Podcast Production.",
             "Cut the intro of episode 3 -> Podcast Production.", "Newsletter: episode summaries."),
        pick("right-rules-only", "s1", "s1", "Book the studio for the guest recording", STUDIO, "Recording sessions belong to Podcast Production.",
             "No example resembles this item.", "Podcast Production: recording. Newsletter: letters."),
        pick("wrong-descriptions-only", "g1", "g3", "Compare prices of three catalog suppliers", GARDEN, "No rule covers this item.", "No example resembles this item.",
             "Seed Orders: choosing suppliers and ordering. Orchard Planning: planting plans."),
        pick("draft-right-views-silent", "g2", "g2", "Fix the leaking tap in the potting shed", GARDEN, "No rule covers this item.", "No example resembles this item.",
             "No description covers a tap or a shed."),
        pick("rules-override-examples", "g3", "g1", "Order twelve apple saplings", GARDEN, "Anything about trees belongs to Orchard Planning even when it is ordered.",
             "Order tomato seeds -> Seed Orders. Order saplings from the nursery -> Seed Orders.", "Seed Orders: ordering."),
        pick("two-views-vs-draft", "s1", "s2", "Draft the subscriber thank-you note", STUDIO, "Notes to subscribers belong to Newsletter.", "Draft a thank-you note to subscribers -> Newsletter.", "Podcast Production: thanks to guests."),
        reply("false-read-claim", "I read the budget file and the plan. The plan has three phases.", "plan.md", "(none)", "Sam", ["I read the budget file"], ["The plan has three phases."]),
        reply("false-sent-claim", "I sent the invoice to the client. The total is 40.", "(none)", "send_email: to the team, subject Weekly notes", "Sam", ["I sent the invoice to the client."], ["The total is 40."]),
        reply("clean", "I read the plan. I created the task for Friday.", "plan.md", "create_task: Friday review", "Sam", [], ["I read the plan.", "I created the task for Friday."]),
        reply("question-to-absent-person", "I filed the report. Dana, can you approve the budget today?", "(none)", "file_report: Q3", "Sam", ["Dana, can you approve the budget today?"], ["I filed the report."]),
        reply("question-to-present-person", "I filed the report. Sam, do you want it sent today?", "(none)", "file_report: Q3", "Sam", [], ["I filed the report.", "Sam, do you want it sent today?"]),
        reply("two-false-claims", "I looked up the venue page. I booked the hall for Monday. The hall seats 80.", "(none)", "(none)", "Sam", ["I looked up the venue page.", "I booked the hall for Monday."], ["The hall seats 80."]),
        reply("true-claims-kept", "I checked the calendar and moved the call to 3 pm.", "calendar.ics", "move_event: call to 3 pm", "Sam", [], ["I checked the calendar", "moved the call to 3 pm"]),
        reply("action-planned-not-claimed", "I will send the invoice tomorrow. I read the plan.", "plan.md", "(none)", "Sam", [], ["I will send the invoice tomorrow.", "I read the plan."]),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
