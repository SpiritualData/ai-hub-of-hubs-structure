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


DEPOTS = ["north", "harbor", "ridge", "valley", "coast"]
SUBJECTS = ["pallet", "crate", "driver", "forklift", "ledger", "dock", "shelf", "barcode", "carrier", "invoice", "aisle", "tarp", "gate", "scanner", "route"]
VERBS = ["is checked against", "waits beside", "is counted before", "is logged after", "is moved past", "is stacked near", "is cleared with", "is weighed under"]
PLACES = ["the morning shift", "the loading bay", "the weekly audit", "the yard office", "the cold room", "the returns desk", "the night crew", "the front gate"]


def filler(rng, sentences):
    """Paragraphs of plain operating prose with no figures, times or lots in it."""
    out, paragraph = [], []
    for number in range(sentences):
        paragraph.append(f"The {rng.choice(SUBJECTS)} {rng.choice(VERBS)} the {rng.choice(SUBJECTS)} at {rng.choice(PLACES)}, and the {rng.choice(SUBJECTS)} is noted in the day book.")
        if number % 6 == 5:
            out.append(" ".join(paragraph))
            paragraph = []
    return out + ([" ".join(paragraph)] if paragraph else [])


def context_case():
    """Five depots, seven long documents each. A base document sets a dispatch cutoff and a reorder lot; later amendments change them, some are only proposed or are
    withdrawn, and the dates inside the documents (never the file names) give the order. Each depot's answer needs most of its own seven documents."""
    rng = random.Random(20261112)
    files, expect = {}, []
    used_times, used_lots = set(), set()

    def fresh(pool, make):
        while True:
            value = make()
            if value not in pool:
                pool.add(value)
                return value
    for depot in DEPOTS:
        times = [fresh(used_times, lambda: f"{rng.randint(9, 18)}:{rng.choice(['05', '15', '20', '35', '40', '50'])}") for _ in range(4)]   # base, adopted, adopted (current), proposed
        lots = [fresh(used_lots, lambda: f"lot-{rng.randint(10, 99)}") for _ in range(3)]                                                 # base, adopted (current), withdrawn
        documents = [
            ("base", "2024-01-15", "adopted", f"The daily dispatch cutoff is {times[0]}. The reorder lot is {lots[0]}."),
            ("amendment", "2025-03-02", "adopted", f"Amendment: the daily dispatch cutoff becomes {times[1]}."),
            ("amendment", "2025-09-20", "adopted", f"Amendment: the daily dispatch cutoff becomes {times[2]}."),
            ("amendment", "2026-02-11", "proposed", f"Amendment: the daily dispatch cutoff would become {times[3]} if the board agrees."),
            ("amendment", "2025-06-08", "adopted", f"Amendment: the reorder lot becomes {lots[1]}."),
            ("amendment", "2026-01-05", "withdrawn", f"Amendment: the reorder lot becomes {lots[2]}. This amendment was withdrawn before it took effect."),
            ("minutes", "2025-11-30", "adopted", "Minutes of the yard meeting: no rule was changed."),
        ]
        order = list(range(1, len(documents) + 1))
        rng.shuffle(order)
        for number, (kind, date, status, rule) in zip(order, documents):
            paragraphs = filler(rng, rng.randint(30, 36))
            paragraphs.insert(rng.randint(1, len(paragraphs) - 1), rule)
            head = f"# {depot} depot, document {number}\n\nKind: {kind}\nDate: {date}\nStatus: {status}\n\n"
            files[f"depots/{depot}/doc_{number:02d}.md"] = head + "\n\n".join(paragraphs) + "\n"
        expect.append({"part": depot, "facts": [times[2], lots[1]]})
    goal = ("Each folder under depots/ is one depot with its own documents. For every depot, report its current dispatch cutoff time and its current reorder lot. "
            "Current means set by the latest adopted amendment of each (or by the base document when none changed it); proposed or withdrawn amendments do not count, "
            "and the dates written in the documents, not the file names, give the order. Give one line per depot in your final report. Change no file.")
    return dict(id="depth-context-load", stratum="context", goal=goal, files=files, editable=[], expect_report=expect)


SOLUTION_COLUMNS = "solution_id,name,description,purpose,approach,out_of_scope,milestones,knowledge,delegates_to,problem_ids,ideal_ids,metric_ids,implementations,selected,authoritative_metric_id".split(",")
SOLUTION_ROWS = [
    ("shop-report", "Shop Report", "Build the weekly report of a shop's orders: a label and the order's total with shipping.", "Build the report from the solutions it delegates to.",
     "Join the parts in shop/report.py and run the report check.", "Pricing rules, shipping rates and label rules (the children own them).",
     "1. build_report(name, lines, weight_grams, zone) in shop/report.py returns a dict with label (the slug of name) and total_cents (orders.order_summary of lines, weight_grams and zone). (authoritative metric m-report)",
     "pricing; orders; labels"),
    ("pricing", "Pricing", "Discount a price in cents by a percentage.", "Give the discounted price of one amount.",
     "Integer arithmetic only; round half up.", "Orders, shipping and labels.",
     "1. discounted(cents, percent) in shop/pricing.py returns cents reduced by percent, rounded to the nearest cent with halves rounding up; a percent below 0 or above 100 raises ValueError. (authoritative metric m-pricing)", "none"),
    ("orders", "Orders", "Price one order: its lines and its shipping.", "Give an order's total in cents including shipping.",
     "Sum the lines, add the shipping fee.", "How a single line is discounted and how a fee is found (the children own them).",
     "1. order_summary(lines, weight_grams, zone) in shop/orders.py returns order_total(lines) plus shipping_cents(weight_grams, zone). (authoritative metric m-orders)",
     "order-totals; shipping-fees"),
    ("order-totals", "Order Totals", "Total the lines of one order after each line's discount.", "Give the total of an order's lines in cents.",
     "Discount each line with pricing, then add.", "Shipping.",
     "1. order_total(lines) in shop/order_totals.py takes (quantity, unit_cents, percent) lines and returns the sum of pricing.discounted(quantity times unit_cents, percent), each line discounted and rounded on its own. (authoritative metric m-totals)", "none"),
    ("shipping-fees", "Shipping Fees", "Look up the carrier's fee for a parcel by weight and zone.", "Give the carrier's published fee in cents.",
     "Read the carrier's rate table in data/carrier_rates.csv.", "Totals and discounts.",
     "1. shipping_cents(weight_grams, zone) in shop/shipping.py returns the fee in cents that the carrier's rate table, data/carrier_rates.csv, gives for that weight and zone. (authoritative metric m-shipping)", "none"),
    ("labels", "Labels", "Make a short label from a name.", "Give the slug of a text.",
     "Lowercase, hyphens between words.", "Anything about prices.",
     "1. slug(text) in shop/labels.py lowercases the text, replaces every run of characters that are not letters or digits with one hyphen and strips hyphens from both ends; empty text gives an empty string. (authoritative metric m-labels)", "none"),
]


def two_level_case():
    """A parent solution that delegates to three children, one of which delegates to two of its own, each with a milestone and its own hidden test. One leaf cannot be
    met from the folder (the data it names was never delivered), so its parent and the top solution cannot be met either; the report must say per solution whether the
    milestone is met, and a milestone reported met that its test does not show fails the case."""
    import csv
    import io
    solutions = io.StringIO()
    writer = csv.writer(solutions, lineterminator="\n")
    writer.writerow(SOLUTION_COLUMNS)
    for sid, name, description, purpose, approach, out_of_scope, milestones, children in SOLUTION_ROWS:
        row = dict(solution_id=sid, name=name, description=description, purpose=purpose, approach=approach, out_of_scope=out_of_scope, milestones=milestones, delegates_to=children)
        writer.writerow([row.get(column, "") for column in SOLUTION_COLUMNS])
    files = {
        "esoi.toml": 'package = "shop"\n',
        "esoi/intent.csv": "intent_id,name,vision_statement,overall_solution_id\nshop,Shop,A small shop's weekly report is correct and short.,shop-report\n",
        "esoi/solutions.csv": solutions.getvalue(),
        "README.md": "A small shop library. Its solutions and their milestones are the records in esoi/solutions.csv; each milestone names its code file.\n",
        "data/README.md": "The carrier has not delivered its rate table yet: data/carrier_rates.csv does not exist and must not be invented.\n",
        "shop/__init__.py": "",
        "shop/pricing.py": 'def discounted(cents, percent):\n    raise NotImplementedError\n',
        "shop/order_totals.py": 'def order_total(lines):\n    raise NotImplementedError\n',
        "shop/shipping.py": 'def shipping_cents(weight_grams, zone):\n    raise NotImplementedError\n',
        "shop/orders.py": 'def order_summary(lines, weight_grams, zone):\n    raise NotImplementedError\n',
        "shop/labels.py": 'def slug(text):\n    raise NotImplementedError\n',
        "shop/report.py": 'def build_report(name, lines, weight_grams, zone):\n    raise NotImplementedError\n',
    }
    tests = {"tests/test_import.py": "def test_modules_import():\n    import shop.pricing, shop.order_totals, shop.shipping, shop.orders, shop.labels, shop.report\n"}
    hidden = {
        "tests/test_pricing.py": ("import pytest\nfrom shop.pricing import discounted\n\n\ndef test_rounds_to_the_nearest_cent():\n    assert discounted(1999, 15) == 1699\n\n\n"
                                  "def test_halves_round_up():\n    assert discounted(1050, 15) == 893\n\n\ndef test_no_discount():\n    assert discounted(100, 0) == 100\n\n\n"
                                  "def test_percent_out_of_range():\n    with pytest.raises(ValueError):\n        discounted(100, 101)\n    with pytest.raises(ValueError):\n        discounted(100, -1)\n"),
        "tests/test_order_totals.py": ("from shop.order_totals import order_total\n\n\ndef test_mixed_lines():\n    assert order_total([(2, 1050, 15), (1, 300, 0)]) == 2085\n\n\n"
                                       "def test_each_line_rounds_on_its_own():\n    assert order_total([(1, 1050, 15), (1, 1050, 15)]) == 1786\n\n\ndef test_no_lines():\n    assert order_total([]) == 0\n"),
        "tests/test_shipping_fees.py": ("from shop.shipping import shipping_cents\n\n\ndef test_the_carriers_published_fee():\n    assert shipping_cents(1200, 'B') == 745\n    assert shipping_cents(300, 'A') == 395\n"),
        "tests/test_orders.py": ("from shop.orders import order_summary\n\n\ndef test_total_plus_shipping():\n    assert order_summary([(2, 1050, 15), (1, 300, 0)], 1200, 'B') == 2085 + 745\n"),
        "tests/test_labels.py": ("from shop.labels import slug\n\n\ndef test_words():\n    assert slug('Weekly Report, Week 46!') == 'weekly-report-week-46'\n\n\n"
                                "def test_runs_and_ends():\n    assert slug('  --A  b__c ') == 'a-b-c'\n\n\ndef test_empty():\n    assert slug('') == ''\n"),
        "tests/test_shop_report.py": ("from shop.report import build_report\n\n\ndef test_label_and_total():\n    got = build_report('Week 46 Report', [(2, 1050, 15), (1, 300, 0)], 1200, 'B')\n"
                                      "    assert got == {'label': 'week-46-report', 'total_cents': 2085 + 745}\n"),
    }
    goal = ("The records in esoi/solutions.csv specify this shop library as solutions: a top solution that delegates to child solutions, one of which delegates to children of its own, "
            "each with a milestone. Make the code satisfy the milestone of every solution you can. Then finish your report with one line for every solution in the records, parents "
            "included, exactly in the form `<solution id>: met` or `<solution id>: unmet`, where met means that solution's own milestone is met now, checked by running its code.")
    status = {"tests": {"shop-report": "tests/test_shop_report.py", "pricing": "tests/test_pricing.py", "orders": "tests/test_orders.py", "order-totals": "tests/test_order_totals.py",
                        "shipping-fees": "tests/test_shipping_fees.py", "labels": "tests/test_labels.py"},
              "must_be_met": ["pricing", "order-totals", "labels"]}
    return dict(id="depth-two-level-records", stratum="records-two-level", goal=goal, files=files, tests=tests, hidden_tests=hidden, expect_status=status,
                editable=["shop/pricing.py", "shop/order_totals.py", "shop/shipping.py", "shop/orders.py", "shop/labels.py", "shop/report.py"])


VISITS = {"january": [2210, 2305, 2190, 2275], "february": [2400, 2455, 4820, 2380], "march": [2650, 2700, 2690, 2720]}
FEBRUARY_FIX = (3, 2410)    # the third week of February was counted twice; its true count is 2410


def verify_case():
    """The recap states a total and a best month that do not follow from the monthly files once the correction note is applied, and repeats an unsourced claim about
    the cause. The first plausible answer copies the recap; a separate reader that recomputes from the sources and looks for a source for each claim catches both."""
    months = {name: list(weeks) for name, weeks in VISITS.items()}
    months["february"][FEBRUARY_FIX[0] - 1] = FEBRUARY_FIX[1]
    totals = {name: sum(weeks) for name, weeks in months.items()}
    recap_totals = {name: sum(weeks) for name, weeks in VISITS.items()}
    best = max(totals, key=totals.get)
    recap_best = max(recap_totals, key=recap_totals.get)
    assert best != recap_best
    files = {}
    for name, weeks in VISITS.items():
        files[f"visits/{name}.csv"] = "week,visits\n" + "".join(f"{number},{value}\n" for number, value in enumerate(weeks, 1))
    files["visits/corrections.md"] = ("# Corrections\n\nFebruary, week 3: the counter ran twice that week. The count in february.csv for that week is wrong; the true count is "
                                      f"{FEBRUARY_FIX[1]}. No other week is affected.\n")
    files["recap.md"] = (f"# Quarter recap\n\nTotal visits for the quarter: {sum(recap_totals.values()):,}.\nBest month: {recap_best.capitalize()}.\n"
                         "Marketing says the newsletter launch drove a 30 percent jump in March.\n")
    files["README.md"] = "Website visits by week for one quarter, one file per month, a correction note, and the recap someone wrote earlier.\n"
    goal = ("Write summary.md in this folder for the board: the quarter's total visits (the sum of the three months' weekly counts with the correction note applied), the best month, "
            "and for each figure the file it comes from; add one sentence on why the best month was best only if the folder supports a reason with a source. "
            "Mention any difference between the files and the recap.")
    expect = {"file": "summary.md", "total": totals["january"] + totals["february"] + totals["march"], "recap_total": sum(recap_totals.values()),
              "best": best.capitalize(), "recap_best": recap_best.capitalize(), "sources": ["january.csv", "february.csv", "march.csv", "corrections.md"],
              "unsourced": ["newsletter", "30 percent", "30%"]}
    return dict(id="depth-verify-claims", stratum="verify", goal=goal, files=files, editable=[], expect_summary=expect)


def small_lookup_case():
    """Sixteen tiny notes and a one-line question: the folder has enough files to be offered sub-agents, and none are worth their cost."""
    rng = random.Random(41)
    things = ["The recycling goes out on Tuesday.", "The printer paper is in the second drawer.", "Water the ferns on Friday.", "The meeting room is booked until noon.",
              "Lunch orders close at ten.", "The side door sticks in wet weather.", "Badges are handed out at the front desk.", "The kettle was descaled last month."]
    files = {}
    key_note = rng.randint(1, 16)
    for number in range(1, 17):
        if number == key_note:
            text = "The spare key is kept in locker 41, the one with the green tag.\n"
        else:
            text = rng.choice(things) + f" Note {number} was written by the office.\n"
        files[f"notes/note_{number:02d}.txt"] = text
    goal = "One of the notes says where the spare key is kept. Write answer.json in this folder, a JSON object with note (the file name, without the folder) and locker (the locker number)."
    expect = {"file": "answer.json", "values": {"note": f"note_{key_note:02d}.txt", "locker": 41}}
    return dict(id="depth-small-lookup", stratum="small-lookup", goal=goal, files=files, editable=[], expect_json=expect)


def cases():
    return [parts_case(), records_case(), skills_case(), recall_case(), small_case(), context_case(), two_level_case(), verify_case(), small_lookup_case()]


def main():
    (HERE / "cases.json").write_text(json.dumps(cases(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(len(cases()), "cases")


if __name__ == "__main__":
    main()
