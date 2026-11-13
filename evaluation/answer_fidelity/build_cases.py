"""Rebuild cases.json for Answer Fidelity from invented requests and answers, four kinds, each with the restated goal an agent might be holding instead of the person's words.

    python3 evaluation/answer_fidelity/build_cases.py

A case is ``input`` (the person's own first message, verbatim), ``answer`` (what the session ended with), ``paraphrase`` (the agent's own restatement of the goal) and ``expect_pass``.
Kinds: ``drift`` (the answer is about something else, or invents a task: must be flagged), ``partial`` (the answer does one asked part and not the other: must be flagged),
``correct`` (the answer does every asked part about the named subject: must pass) and ``honest_none`` (the answer says plainly, with what was looked at, that nothing was found about the
named subject, and gives its own view of that: must pass). For a drift or partial case the paraphrase is the restatement such an answer would have been written to satisfy (the
goal as the agent had narrowed or moved it); for the other two it is a faithful short restatement. The subjects are everyday and invented. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

DRIFT = [
    ("Ask a helper to look through my sourdough notes for something surprising, then tell me what you make of it.",
     "Decisions for you: 1. Approve the pilot plan for the autumn workshop series. 2. Confirm the ledger format for the shared budget. 3. Choose a revenue target for the spring program. What I changed: Nothing.",
     "Review the pending decisions in the planning material and list them for the person."),
    ("Have a cheap helper find the most interesting pattern in my hiking log and then give me your own take on it.",
     "The helper reported that the permit paperwork for the car park is due on the first of the month and that the insurance renewal quote rose by a tenth. I recommend renewing the insurance with the same provider and filing the permit form this week.",
     "Summarise what is outstanding in the paperwork and recommend next steps."),
    ("What stands out in my chess game notes? Use a subagent to look first, then add your view.",
     "I looked through the invoice list. Three vendors were paid twice in March, and the largest duplicate is for the printing service. I suggest asking each vendor for a credit note and adding a duplicate check to the monthly routine.",
     "Review the records for anything unusual and recommend fixes."),
    ("Look at my houseplant watering schedule with a helper and tell me one thing that looks off, plus what you would change.",
     "The email service migration has two open items: the sending domain needs a new verification record and the old mailbox forwarding should be switched off. I would finish the record first, then retire the forwarding after a week of clean delivery.",
     "Check the current project for open items and say what to change."),
    ("Find something interesting in my bike maintenance notes using a helper, then say what you think it means.",
     "Here is a plan for a neighbourhood bike share. Step 1: survey twenty households. Step 2: pick three docking spots near the library. Step 3: price a pilot of ten bikes. Step 4: ask the council for a small grant. Step 5: review after a month.",
     "Come up with a useful plan for the person's cycling interests."),
]
PARTIAL = [
    ("Use a helper to list the three oldest entries in my bread log, and then say which of them you would redo.",
     "The helper listed the three oldest entries in the bread log: the rye loaf from 3 January, the honey oat loaf from 9 January and the plain white loaf from 14 January.",
     "List the three oldest entries in the bread log."),
    ("Summarize my reading notes on volcanoes in two sentences and suggest one follow-up book.",
     "Your volcano notes cover how shield and stratovolcanoes differ, why eruptions at subduction zones are explosive, and the 1980 eruption of a well-known peak. They end with open questions about how long warning signs last before an eruption.",
     "Summarise the volcano reading notes."),
    ("Check my running log for the week with the highest mileage and compare it to the previous week.",
     "The week of 12 May has the highest mileage in the log, at 41 miles over five runs.",
     "Find the highest-mileage week in the running log."),
    ("Use a helper to find what my gardening notes say about tomatoes, then give your own advice for next season.",
     "The helper found that the notes mention tomatoes in three places: the 2023 plants got blight in August, the 2024 plants were staked late, and the cherry variety out-produced the beefsteak both years.",
     "Find what the gardening notes say about tomatoes."),
    ("Look in my chess notes for my most common mistake and propose a drill to fix it.",
     "Your most common mistake in the notes is leaving a piece undefended after a trade; it appears in eleven of the logged games, most often in the middlegame.",
     "Find the most common mistake in the chess notes."),
]
CORRECT = [
    ("Use a helper to find something interesting in my sourdough notes, then give your own view on what it finds.",
     "A helper read the sourdough notes. The interesting pattern: every loaf you rated highest was fed twice the evening before and proofed in the fridge overnight, while the loaves proofed on the counter were rated lower in all seven cases. My view: the cold proof is doing the work, probably by slowing fermentation enough to develop flavour, so keep the double feed as a constant and test the proof length next, say 12 against 18 hours.",
     "Find something interesting in the sourdough notes with a helper and give a view."),
    ("Summarize my reading notes on volcanoes in two sentences and suggest one follow-up book.",
     "Your notes explain that shield volcanoes erupt runny lava gently while stratovolcanoes at subduction zones build pressure and erupt explosively, and you keep returning to how reliable the warning signs are before an eruption. A good follow-up for that question is a general-audience book on volcano monitoring and forecasting.",
     "Summarise the volcano notes in two sentences and suggest a book."),
    ("Check my running log for the week with the highest mileage and compare it to the previous week.",
     "The week of 12 May is the highest at 41 miles over five runs. The week before it was 33 miles over four runs, so the peak week added eight miles and one run, a rise of about a quarter, which is more than the ten percent increase usually advised.",
     "Find the highest-mileage week and compare it with the one before."),
    ("Use a helper to find what my gardening notes say about tomatoes, then give your own advice for next season.",
     "The helper found three mentions: blight in August 2023, late staking in 2024, and the cherry variety beating the beefsteak both years. My advice: stake at planting, water at the base and space the plants wider to limit blight, and plant more cherry tomatoes than beefsteak, since the notes show they are the reliable ones.",
     "Find what the gardening notes say about tomatoes with a helper and advise for next season."),
    ("Look in my chess notes for my most common mistake and propose a drill to fix it.",
     "The most common mistake in the notes is leaving a piece undefended after a trade, in eleven logged games. A drill for it: before every capture or recapture, say out loud which of your pieces are undefended afterwards, and practise on twenty tactics puzzles a day where the first step is listing loose pieces.",
     "Find the most common chess mistake and propose a drill."),
]
HONEST_NONE = [
    ("Use a helper to find something interesting about my beekeeping notes and give your own insight.",
     "The helper searched the notes folder and found no beekeeping notes: the files were about gardening and cooking, which I set aside because they are about other subjects. So there is nothing interesting about beekeeping to report from them. My own view is that if you intend to keep such notes, logging hive weight and inspection dates from the start would give you something to learn from by autumn.",
     "Find something interesting about the beekeeping notes and give an insight."),
    ("Find out from my astronomy notes which planet I have observed most, using a helper, and tell me what you make of it.",
     "The helper looked in every file of the folder and found no astronomy notes at all, only a shopping list and a travel itinerary, so I cannot say which planet you observed most. My own view: a simple observation log with date, planet and conditions would answer this question within a few weeks of use.",
     "Find the most-observed planet in the astronomy notes and comment."),
    ("Have a helper check my knitting notes for the pattern I used most and then say what you would try next.",
     "The helper found no knitting notes: the folder holds receipts and a calendar export, which are about something else, so I cannot name a most-used pattern. If the notes are somewhere else, tell me where and I will look; meanwhile my suggestion for a next project is a simple scarf pattern with a ribbed edge, a good way to start logging patterns.",
     "Find the most-used knitting pattern and suggest what to try next."),
]


def main():
    cases = []
    for kind, rows, expect_pass in (("drift", DRIFT, False), ("partial", PARTIAL, False), ("correct", CORRECT, True), ("honest_none", HONEST_NONE, True)):
        for index, (given, answer, paraphrase) in enumerate(rows, 1):
            cases.append({"id": f"fidelity-{kind}-{index:02d}", "kind": kind, "args": {"input": given, "answer": answer, "paraphrase": paraphrase}, "expect": expect_pass})
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
