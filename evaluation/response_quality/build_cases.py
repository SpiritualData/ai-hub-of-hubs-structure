"""Rebuild cases.json for Response Quality: invented, neutral responses with the evidence text they are held to, so no model is called.

Each case gives a ``response`` and the ``evidence`` behind it. ``expect`` maps an arm to the findings it must return; an arm not named must return none, so a response
that breaks one rule also shows that the other arms stay quiet. The expected findings are written by hand from the rule, never produced by an arm.

Families (the ``kind`` of a case, reported separately):
  figure   a figure the evidence holds is kept; one it does not hold is a finding; list numbers and the evidence's own figures are not.
  dash     an em dash is a finding (one count per response); none is none.
  date     "N days from today" and "N days before/after an event (date)" must equal the real distance between the dates the text states.
  link     a link the evidence does not contain is a finding.
  clean    a response that breaks no rule returns nothing from every arm.

    python3 evaluation/response_quality/build_cases.py

Standard library only. The em dash is written as an escape so this file holds none."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASH = "—"
TODAY = "Today is 2026-07-12. Deadline 20 Jul, 8 days away; 5 and 3 are other counts."


def case(name, kind, response, evidence="", **expect):
    return {"id": "quality-" + name, "kind": kind, "args": {"response": response, "evidence": evidence}, "expect": expect}


def main():
    cases = [
        case("figure-held", "figure", "The garden has 12 beds and 4 are planted.", "Garden notes: 12 beds, 4 planted."),
        case("figure-invented", "figure", "The garden has 12 beds and 9 are planted.", "Garden notes: 12 beds, 4 planted.",
             grounded_figures=["figure not in the evidence: 9"]),
        case("figure-list-numbers-ignored", "figure", "Steps:\n1. Water the beds.\n2. Pull weeds from 4 beds.", "Garden notes: 4 beds need weeding."),
        case("figure-two-invented", "figure", "We sold 30 jars. Then 45 more went out the door.", "Sales sheet: 12 jars sold.",
             grounded_figures=["figure not in the evidence: 30", "figure not in the evidence: 45"]),
        case("dash-one", "dash", f"The plan {DASH} which you wrote {DASH} works.", "", em_dash_free=["em dash in the response: 2"]),
        case("dash-range", "dash", f"Open 10{DASH}20 hours.", "Open 10 to 20 hours.", em_dash_free=["em dash in the response: 1"], grounded_figures=[]),
        case("dash-none", "dash", "The plan, which you wrote, works.", ""),
        case("date-days-from-today-right", "date", "On 20 Jul that is 8 days from today.", TODAY),
        case("date-days-from-today-wrong", "date", "On 20 Jul that is 5 days from today.", TODAY,
             date_arithmetic=["8 days from today to 20 Jul, not 5"], grounded_figures=[]),
        case("date-other-anchor-not-judged", "date", "Finish 3 days before they arrive on 20 Jul.", TODAY),
        case("date-offset-right", "date", "We arrive 13 Nov. Pack 3 days before arrival (10 Nov).", "Trip: arrive 13 Nov, pack 10 Nov, 3 days."),
        case("date-offset-wrong", "date", "We arrive 13 Nov. Pack 3 days before arrival (17 Nov).", "Trip: arrive 13 Nov, 3 days.",
             date_arithmetic=["3 days before 13 Nov is 10 Nov, not 17 Nov"], grounded_figures=["figure not in the evidence: 17"]),
        case("link-held", "link", "See https://example.org/a for details.", "Source: https://example.org/a"),
        case("link-invented", "link", "See https://example.org/b for details.", "Source: https://example.org/a",
             evidence_check=["link not in the evidence: https://example.org/b"]),
        case("clean", "clean", "The garden is doing well and the beds are planted.", "Garden notes: planted."),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
