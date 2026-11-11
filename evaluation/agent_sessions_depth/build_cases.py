"""Write cases.json for the depth stage of Delegated Agent Sessions: five public, synthetic cases built here in code.

The hard stage's cases can each be done in one session with no depth, so an arm that uses sub-agents, recalled context or a consumer's skills
cannot win there and an arm without them cannot lose. These five cases each need something the hard set does not:

* ``depth-parts-sites`` (stratum ``parts``): five separable sites of many files each, most irrelevant to a given part; facts are checked per part.
* ``depth-solution-records`` (``records``): the folder carries solution records (a parent delegating to three children, each with a milestone,
  and a retired one); the code must satisfy each child's milestone, checked by hidden tests per child.
* ``depth-skills-folder`` (``skills``): the rule the work needs is in a skill file in a skills folder outside the work folder (``skills`` holds
  that folder's files; the scorer writes it beside the work folder and hands its path only to an arm that can take it).
* ``depth-recall-known`` (``recall``): ``known`` is a short finding from an earlier investigation that saves searching; the folder holds a
  planted wrong claim that must be verified and rejected.
* ``depth-small-simple`` (``small``): a one-line fix in a tiny folder, where sub-agents are pure waste; the score is the same, the cost shows it.

Run ``python3 evaluation/agent_sessions_depth/build_cases.py`` to rewrite ``cases.json``; the test that pins the file to this code fails otherwise.
Everything is deterministic and neutral (a plant nursery's sensors, a small report library, a shop's shipping rules); no private text.
Standard library only."""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

SITES = ["alder", "birch", "cedar", "dune", "elm"]
FILES_PER_SITE = 7
ROWS_PER_FILE = 60


def parts_case():
    rng = random.Random(20261111)
    files, expect = {}, []
    alert_sensors = rng.sample(range(13, 90), len(SITES) * 2)
    for number, site in enumerate(SITES):
        open_file, closed_file = rng.sample(range(1, FILES_PER_SITE + 1), 2)
        open_sensor, closed_sensor = (f"S-{alert_sensors[2 * number]}", f"S-{alert_sensors[2 * number + 1]}")
        open_date, closed_date = f"2026-04-{rng.randint(10, 28):02d}", f"2026-02-{rng.randint(10, 27):02d}"
        offset, old_offset = f"0.{rng.randint(30, 99)}", f"0.{rng.randint(10, 29)}"
        for index in range(1, FILES_PER_SITE + 1):
            rows = ["date,sensor,value"]
            for _ in range(ROWS_PER_FILE):
                rows.append(f"2026-03-{rng.randint(1, 28):02d},S-{rng.randint(1, 12):02d},{rng.uniform(5, 40):.2f}")
            if index == open_file:
                rows.insert(rng.randint(2, ROWS_PER_FILE), f"#ALERT,{open_sensor},{open_date},open")
            if index == closed_file:
                rows.insert(rng.randint(2, ROWS_PER_FILE), f"#ALERT,{closed_sensor},{closed_date},closed")
            files[f"sites/{site}/readings_{index:02d}.csv"] = "\n".join(rows) + "\n"
        files[f"sites/{site}/config.json"] = json.dumps({"site": site, "unit": "mm", "calibration_offset": float(offset)}, indent=1) + "\n"
        files[f"sites/{site}/notes.md"] = (f"# {site}\n\nThe calibration offset was {old_offset} until the March recalibration; config.json holds the current one.\n"
                                           f"Closed alerts stay in the readings files for the record. Only an alert whose last field is open is current.\n")
        expect.append({"part": site, "facts": [open_sensor, open_date, offset]})
    goal = ("Each folder under sites/ is one site. For every site, report the sensor id and the date of its one current (open) alert, and its current "
            "calibration offset. Give them in your final report, one line per site. Change no file.")
    return dict(id="depth-parts-sites", stratum="parts", goal=goal, files=files, editable=[], expect_report=expect)


def records_case():
    files = {
        "esoi/parent.md": ("# Solution: report-builder\n\nPurpose: build the weekly report.\n\nDelegates to: totals, week-dates, labels\n\n"
                           "Retired, never build: rounding\n"),
        "esoi/totals.md": ("# Solution: totals\n\nCode: report/totals.py\n\nMilestone: total_cents(lines) takes (quantity, unit_cents) pairs and returns the "
                           "integer sum of quantity times unit_cents; no lines gives 0; a negative quantity raises ValueError.\n"),
        "esoi/week-dates.md": ("# Solution: week-dates\n\nCode: report/week_dates.py\n\nMilestone: week_start(iso_date) takes a date string YYYY-MM-DD and "
                               "returns the Monday of its ISO week, as a string in the same form.\n"),
        "esoi/labels.md": ("# Solution: labels\n\nCode: report/labels.py\n\nMilestone: slug(text) lowercases the text, replaces every run of characters "
                           "that are not letters or digits with one hyphen, and strips hyphens from both ends; empty text gives an empty string.\n"),
        "esoi/rounding.md": "# Solution: rounding\n\nRetired. Code: report/rounding.py stays as it is.\n",
        "report/__init__.py": "",
        "report/totals.py": 'def total_cents(lines):\n    """Sum of quantity times unit_cents over (quantity, unit_cents) pairs."""\n    raise NotImplementedError\n',
        "report/week_dates.py": 'def week_start(iso_date):\n    """The Monday of the ISO week of a YYYY-MM-DD date."""\n    raise NotImplementedError\n',
        "report/labels.py": 'def slug(text):\n    """A lowercase hyphen-separated label."""\n    raise NotImplementedError\n',
        "report/rounding.py": 'def round_half_even(value):\n    raise NotImplementedError\n',
        "README.md": "A small report library. Its solution records are in esoi/; each child record names its code file and its milestone.\n",
    }
    tests = {"tests/test_import.py": "def test_modules_import():\n    import report.totals, report.week_dates, report.labels\n"}
    hidden = {
        "tests/test_totals.py": (
            "import pytest\nfrom report.totals import total_cents\n\n\ndef test_sum():\n    assert total_cents([(2, 150), (1, 99)]) == 399\n\n\n"
            "def test_empty():\n    assert total_cents([]) == 0\n\n\ndef test_negative_quantity():\n    with pytest.raises(ValueError):\n"
            "        total_cents([(-1, 100)])\n"),
        "tests/test_week_dates.py": (
            "from report.week_dates import week_start\n\n\ndef test_midweek():\n    assert week_start('2026-11-11') == '2026-11-09'\n\n\n"
            "def test_sunday():\n    assert week_start('2026-11-15') == '2026-11-09'\n\n\ndef test_monday():\n    assert week_start('2026-11-09') == '2026-11-09'\n"),
        "tests/test_labels.py": (
            "from report.labels import slug\n\n\ndef test_words():\n    assert slug('Hello, World!') == 'hello-world'\n\n\n"
            "def test_runs_and_ends():\n    assert slug('  --A  b__c ') == 'a-b-c'\n\n\ndef test_empty():\n    assert slug('') == ''\n"),
    }
    goal = ("The solution records in esoi/ describe this library: a parent solution that delegates to child solutions, each with a milestone. Make the "
            "code satisfy the milestone of every child the parent delegates to, and build nothing the records mark as retired.")
    return dict(id="depth-solution-records", stratum="records", goal=goal, files=files, tests=tests, hidden_tests=hidden,
                editable=["report/totals.py", "report/week_dates.py", "report/labels.py"])


SHIPPING_SKILL = """---
name: shipping-rules
description: How this shop prices shipping for an order (fees, free shipping, discount codes, pickup).
---
# Shipping rules

1. The discount code SPRING takes 15 percent off the subtotal. Any other code, or none, changes nothing.
2. Shipping is free when the discounted subtotal is 75.00 or more.
3. Otherwise the shipping fee is 6.40.
4. An order with the code PICKUP pays no shipping at all and gets no discount.
"""

OTHER_SKILLS = {
    "refund-policy": ("---\nname: refund-policy\ndescription: When and how a refund is granted.\n---\n# Refunds\n\nA refund over 50.00 needs a second "
                      "approval. Returned goods are refunded within 14 days.\n"),
    "tone-guide": ("---\nname: tone-guide\ndescription: The voice of customer messages.\n---\n# Tone\n\nShort, warm, no exclamation marks. "
                   "Free shipping is announced in the first line.\n"),
    "naming": "---\nname: naming\ndescription: How files and folders are named.\n---\n# Naming\n\nLowercase words joined by hyphens.\n",
}


def shipping_for(subtotal, code):
    if code == "PICKUP":
        return 0.0
    if code == "SPRING":
        subtotal = subtotal * 0.85
    return 0.0 if subtotal >= 75.0 else 6.40


def skills_case():
    orders = [("o-101", 80.00, ""), ("o-102", 88.00, "SPRING"), ("o-103", 60.00, "SPRING"), ("o-104", 30.00, ""), ("o-105", 120.00, "PICKUP"),
              ("o-106", 74.99, "WELCOME"), ("o-107", 90.00, "SPRING"), ("o-108", 20.00, "PICKUP")]
    fees = {oid: shipping_for(sub, code) for oid, sub, code in orders}
    lines = ["order,subtotal,code"] + [f"{oid},{sub:.2f},{code}" for oid, sub, code in orders]
    skills = {f"{name}/SKILL.md": text for name, text in OTHER_SKILLS.items()}
    skills["shipping-rules/SKILL.md"] = SHIPPING_SKILL
    files = {"orders.csv": "\n".join(lines) + "\n",
             "README.md": "Orders of the week are in orders.csv. Shipping follows the shop's shipping-rules skill; the work folder holds no copy of it.\n"}
    goal = ("Write summary.json in this folder, a JSON object with total_shipping (the sum of the shipping fees of all orders in orders.csv, a number "
            "with at most two decimals) and free_orders (the list of order ids that ship free, including pickups). Price shipping by the shop's "
            "shipping-rules skill.")
    expect = {"file": "summary.json", "values": {"total_shipping": round(sum(fees.values()), 2),
                                                 "free_orders": sorted(oid for oid, fee in fees.items() if fee == 0.0)}}
    return dict(id="depth-skills-folder", stratum="skills", goal=goal, files=files, editable=[], skills=skills, expect_json=expect)


def recall_case():
    rng = random.Random(7)
    files = {
        "config/limits.toml": "[worker]\nmax_attempts = 4\nbackoff_seconds = 30\n\n[uploader]\nmax_attempts = 7\nbackoff_seconds = 5\n",
        "config/settings.ini": "[retry]\nretry_limit = 9\n",
        "worker/loader.py": ('import tomllib\nfrom pathlib import Path\n\n\ndef limits():\n    """The only configuration the worker reads."""\n'
                             '    with (Path(__file__).resolve().parent.parent / "config" / "limits.toml").open("rb") as handle:\n'
                             '        return tomllib.load(handle)\n'),
        "worker/retry.py": ('from worker.loader import limits\n\n\ndef attempts():\n    """How many times the worker tries a job."""\n'
                            '    return limits()["worker"]["max_attempts"]\n'),
        "uploader/retry.py": ('from worker.loader import limits\n\n\ndef attempts():\n    return limits()["uploader"]["max_attempts"]\n'),
        "NOTES.md": ("# Notes\n\nThe retry limit is 9: it is the retry_limit in config/settings.ini, confirmed by the operations team last spring.\n"
                     "The backoff is a fixed 30 seconds.\n"),
    }
    for index in range(1, 25):
        name = f"worker/job_{index:02d}.py"
        files[name] = (f'"""Job kind {index}."""\n\n\ndef run(payload):\n    total = 0\n' +
                       "".join(f"    total += len(str(payload.get('field_{k}', '')))\n" for k in range(rng.randint(3, 8))) + "    return total\n")
    known = ("Earlier investigation: the worker's retry limit is the max_attempts key of the [worker] table in config/limits.toml, read by "
             "worker/loader.py. Nothing else in the folder is read by the loader; settings.ini is not used by any code.")
    goal = ("What is the effective retry limit of the worker? Write answer.json in this folder, a JSON object with retry_limit (the number) and "
            "source_file (the path, from this folder, of the file the number is read from). Verify any claim in the folder before you use it.")
    expect = {"file": "answer.json", "values": {"retry_limit": 4, "source_file": "config/limits.toml"}}
    return dict(id="depth-recall-known", stratum="recall", goal=goal, files=files, editable=[], known=known, expect_json=expect)


def small_case():
    files = {
        "util/clamp.py": ('def clamp(value, low, high):\n    """Keep value inside [low, high]."""\n    if value < low:\n        return low\n'
                          '    if value > high:\n        return low\n    return value\n'),
        "util/words.py": 'def shout(text):\n    return text.upper() + "!"\n',
        "README.md": "Two tiny helpers.\n",
    }
    tests = {"tests/test_clamp_basic.py": "from util.clamp import clamp\n\n\ndef test_inside():\n    assert clamp(5, 0, 10) == 5\n"}
    hidden = {"tests/test_clamp_edges.py": ("from util.clamp import clamp\n\n\ndef test_below():\n    assert clamp(-3, 0, 10) == 0\n\n\n"
                                            "def test_above():\n    assert clamp(42, 0, 10) == 10\n\n\ndef test_at_the_ends():\n"
                                            "    assert clamp(0, 0, 10) == 0 and clamp(10, 0, 10) == 10\n")}
    goal = "clamp in util/clamp.py returns the wrong value when the input is above the range. Fix it."
    return dict(id="depth-small-simple", stratum="small", goal=goal, files=files, tests=tests, hidden_tests=hidden, editable=["util/clamp.py"])


def cases():
    return [parts_case(), records_case(), skills_case(), recall_case(), small_case()]


def main():
    (HERE / "cases.json").write_text(json.dumps(cases(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(len(cases()), "cases")


if __name__ == "__main__":
    main()
