"""Write cases.json for Delegated Agent Sessions: twelve general tasks that are not coding, each a small folder of plain files, a goal and the facts the
agent's final report must hold. The tasks are what a person hands to an agent: read notes and report, compare two documents, count and list, tidy a
folder's names, answer from several files. They were written for this evaluation and are not drawn from any other case set.

    python3 evaluation/agent_sessions/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

CASES = [
    ("notes-city", {"notes.txt": "Meeting with the grant team.\nPlace: Rotterdam.\nBring the budget sheet.\n"},
     "Read notes.txt and tell me which city the meeting is in.", ["rotterdam"]),
    ("two-prices", {"offer_a.txt": "Offer A: 14 licences at 30 euros each.\n", "offer_b.txt": "Offer B: 10 licences at 41 euros each.\n"},
     "Compare the two offers in this folder and tell me which is cheaper in total and by how much.", ["offer a", "10"]),
    ("count-files", {"a.md": "x", "b.md": "y", "c.txt": "z", "d.md": "w"},
     "How many markdown (.md) files are in this folder? Report the number and list their names.", ["3", "a.md", "b.md", "d.md"]),
    ("deadline", {"plan.txt": "Phase one ends on 12 March.\nPhase two ends 20 days later.\nPhase three starts the day after phase two ends.\n"},
     "Work out the date phase three starts, using plan.txt, and tell me.", ["2 april"]),
    ("who-owns", {"owners.csv": "area,owner\nbilling,Sana\nsupport,Idris\nonboarding,Mei\n", "request.txt": "A customer cannot update the card on file.\n"},
     "Using the two files, tell me who should receive the request and why.", ["sana", "billing"]),
    ("summary-one-line", {"article.txt": "The council approved a new cycling lane on Mill Street. Work starts in May and lasts six weeks. Parking on the north side will be removed during the work.\n"},
     "Summarise article.txt in one sentence that includes the street name and when work starts.", ["mill street", "may"]),
    ("tidy-names", {"Report FINAL (2).txt": "r", "report draft.txt": "d", "Notes_old.TXT": "n"},
     "Propose lowercase names with hyphens instead of spaces for every file in this folder, as a list of old name to new name, and do not rename anything.", ["report-final", "notes-old"]),
    ("totals", {"sales.csv": "month,units\njan,120\nfeb,95\nmar,143\n"},
     "Add up the units in sales.csv and report the total and the best month.", ["358", "mar"]),
    ("contradiction", {"a.txt": "The workshop is on Tuesday at 10:00.\n", "b.txt": "Reminder: the workshop is on Wednesday at 10:00.\n"},
     "The two files disagree about something. Say what they disagree about.", ["tuesday", "wednesday"]),
    ("missing", {"todo.txt": "1. Book the room\n2. Send the agenda\n"},
     "Does todo.txt have a task about catering? Reply 'none found' if not, and quote the last task in the list.", ["none found", "send the agenda"]),
    ("order", {"steps.txt": "C: serve\nA: boil water\nB: add the pasta\n"},
     "Put the steps in steps.txt in the right order by their letters and report the order.", ["boil water", "add the pasta", "serve"]),
    ("names", {"people.txt": "Ana Silva, Bo Chen, Cleo Park\n"},
     "How many people are listed in people.txt and which one has the surname Chen?", ["3", "bo"]),
]


def main():
    cases = [{"id": f"agent-{name}", "files": files, "goal": goal, "expect": expect} for name, files, goal, expect in CASES]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
