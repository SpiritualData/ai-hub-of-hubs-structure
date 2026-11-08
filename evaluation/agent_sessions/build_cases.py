"""Write cases.json for Delegated Agent Sessions: open-ended tasks a person hands to an agent, of three kinds (the case's ``stratum``).

* ``report`` (12): read a small folder of plain files and report; the final report must hold every expected fact and the files stay unchanged.
* ``code`` (3): change a file so that the case's own tests pass; the harness rewrites the tests before checking, so editing them cannot pass.
* ``deliverable`` (3), shaped like the work a milestone asks for: draft a script to a written rubric, research a question from source
  files and cite each one, turn meeting notes into a dated plan. The file the agent writes is checked against the rubric.

They were written for this evaluation and are not drawn from any other case set. The research case uses local source files, not the
web, so it can be checked the same way every time.

    python3 evaluation/agent_sessions/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

REPORTS = [
    ("notes-city", {"notes.txt": "Meeting with the grant team.\nPlace: Rotterdam.\nBring the budget sheet.\n"},
     "Read notes.txt and tell me which city the meeting is in.", ["rotterdam"]),
    # Offer A totals 420 and offer B 410, so B is cheaper by 10.
    ("two-prices", {"offer_a.txt": "Offer A: 14 licences at 30 euros each.\n", "offer_b.txt": "Offer B: 10 licences at 41 euros each.\n"},
     "Compare the two offers in this folder and tell me which is cheaper in total and by how much.", ["offer b", "10"]),
    ("count-files", {"a.md": "x", "b.md": "y", "c.txt": "z", "d.md": "w"},
     "How many markdown (.md) files are in this folder? Report the number and list their names.", ["3", "a.md", "b.md", "d.md"]),
    ("deadline", {"plan.txt": "Phase one ends on 12 March.\nPhase two ends 20 days later.\nPhase three starts the day after phase two ends.\n"},
     "Work out the date phase three starts, using plan.txt, and tell me.", ["2 april"]),
    ("who-owns", {"owners.csv": "area,owner\nbilling,Sana\nsupport,Idris\nonboarding,Mei\n", "request.txt": "A customer cannot update the card on file.\n"},
     "Using the two files, tell me who should receive the request and why.", ["sana", "billing"]),
    ("summary-one-line", {"article.txt": "The council approved a new cycling lane on Mill Street. Work starts in May and lasts six weeks. Parking on the north side will be removed during the work.\n"},
     "Summarise article.txt in one sentence that includes the street name and when work starts.", ["mill street", "may"]),
    ("tidy-names", {"Report FINAL (2).txt": "r", "report draft.txt": "d", "Notes_old.TXT": "n"},
     "Propose new names for every file in this folder: lowercase, with hyphens instead of spaces and underscores. Give a list of old name to "
     "new name and do not rename anything.", ["report-final", "report-draft", "notes-old"]),
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

SLUG_TESTS = '''from slug import slugify


def test_spaces():
    assert slugify("Hello World") == "hello-world"


def test_trims_and_collapses():
    assert slugify("  Spaces  and--dashes ") == "spaces-and-dashes"


def test_drops_punctuation():
    assert slugify("C++ & Python!") == "c-python"


def test_empty():
    assert slugify("") == ""
'''

MEDIAN_TESTS = '''import pytest

from stats import median


def test_odd():
    assert median([3, 1, 2]) == 2


def test_even():
    assert median([4, 1, 3, 2]) == 2.5


def test_does_not_change_input():
    data = [3, 1, 2]
    median(data)
    assert data == [3, 1, 2]


def test_empty():
    with pytest.raises(ValueError):
        median([])
'''

TOTALS_TESTS = '''from pathlib import Path

from totals import totals

HERE = Path(__file__).resolve().parent


def test_totals():
    assert totals(HERE / "expenses.csv") == {"travel": 230.5, "food": 42.0, "books": 19.99}


def test_header_only(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("category,amount\\n")
    assert totals(empty) == {}
'''

CODE = [
    ("code-slugify",
     {"slug.py": 'def slugify(text):\n    """Lowercase words of letters and digits joined by single hyphens."""\n    raise NotImplementedError\n'},
     {"test_slug.py": SLUG_TESTS}, ["slug.py"],
     "Implement slugify in slug.py so that every test in test_slug.py passes. Do not change the tests."),
    ("code-median-bug",
     {"stats.py": "def median(values):\n    s = values\n    s.sort()\n    return s[len(s) // 2]\n"},
     {"test_stats.py": MEDIAN_TESTS}, ["stats.py"],
     "median in stats.py is wrong for some inputs. Fix it so that every test in test_stats.py passes. Do not change the tests."),
    ("code-csv-totals",
     {"totals.py": 'def totals(path):\n    """Sum the amount column of a CSV file per category."""\n    raise NotImplementedError\n',
      "expenses.csv": "category,amount\ntravel,200\nfood,12.5\ntravel,30.5\nbooks,19.99\nfood,29.5\n"},
     {"test_totals.py": TOTALS_TESTS}, ["totals.py"],
     "Implement totals in totals.py so that every test in test_totals.py passes. Do not change the tests or expenses.csv."),
]

DELIVERABLES = [
    ("script-to-rubric",
     {"features.txt": "Product: Lumen Notes\nFeatures:\n- offline sync: notes save without a connection and sync later\n"
                      "- voice capture: speak a note and it is written down\n- shared notebooks: a team edits one notebook together\n",
      "rubric.txt": "Write the script of a 60 to 90 second explainer video.\n- Save it as script.md.\n- 120 to 220 words.\n"
                    "- Three sections with these headings: Hook, Body, Call to action.\n- Name the product and all three features.\n"
                    "- No em dashes.\n"},
     "Draft the video script that rubric.txt asks for, about the product in features.txt. Meet every point of the rubric.",
     dict(file="script.md", min_words=120, max_words=220, contains=["hook", "body", "call to action", "lumen notes", "offline", "voice", "shared"],
          absent=["—"])),
    ("research-and-cite",
     {"sources/city_report.txt": "City transport report, January 2026. Bike share trips rose 18 percent in 2025 compared with 2024, "
                                 "to 2.36 million trips, counted from the docking stations.\n",
      "sources/rider_survey.txt": "Rider survey, 2025, 1,200 respondents. Respondents reported riding more often than in 2024; "
                                  "the operator's trip log behind the survey shows growth of 18 percent.\n",
      "sources/blog_post.txt": "Everyone is cycling now! Bike share basically doubled last year, from what I see on my street.\n"},
     "Using only the files in sources/, answer: by how much did bike share trips change in 2025? Write findings.md with the answer. "
     "After every claim, cite the file it came from in square brackets, for example [sources/city_report.txt]. "
     "Name any source that disagrees and say why it is weaker.",
     dict(file="findings.md", contains=["18", "city_report.txt", "rider_survey.txt", "blog_post.txt"], absent=[])),
    ("plan-from-notes",
     {"notes.txt": "Kickoff notes (rough)\n- Mei will book the venue, needs doing by 14 May\n- budget draft: Idris, 2 May\n"
                   "- someone should send invites... Sana said she would, by 20 May\n- Bo: confirm the caterer by 9 May\n"},
     "Turn notes.txt into plan.md: one line per action with the action, its owner and its due date, ordered from the earliest due date "
     "to the latest.",
     dict(file="plan.md", contains=["idris", "bo", "mei", "sana", "venue", "caterer", "invites", "budget"], absent=[],
          order=["idris", "bo", "mei", "sana"])),
]


def main():
    cases = [{"id": f"agent-{name}", "stratum": "report", "files": files, "goal": goal, "expect": expect} for name, files, goal, expect in REPORTS]
    cases += [{"id": f"agent-{name}", "stratum": "code", "files": files, "tests": tests, "editable": editable, "goal": goal, "expect": []}
              for name, files, tests, editable, goal in CODE]
    cases += [{"id": f"agent-{name}", "stratum": "deliverable", "files": files, "goal": goal, "expect": [], "rubric": rubric}
              for name, files, goal, rubric in DELIVERABLES]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
