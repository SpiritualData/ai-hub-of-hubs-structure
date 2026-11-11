"""A hand-written correct result for each depth case, used only to prove the scorer can pass: it reads the folder the way a person would
(a search of the files, a read of the records, the skills file, the earlier finding) and writes what the goal asks. No model, no cost."""
import csv
import json
import re
from pathlib import Path


class Reply:
    def __init__(self, text):
        self.output, self.met, self.error, self.cost_usd = text, True, "", 0.0
        self.subagent_calls, self.turns = 0, 1


def parts(args):
    lines = []
    for site in sorted(Path(args["root"], "sites").iterdir()):
        for path in sorted(site.glob("readings_*.csv")):
            for row in csv.reader(path.read_text(encoding="utf-8").splitlines()):
                if row and row[0] == "#ALERT" and row[3] == "open":
                    sensor, date = row[1], row[2]
        offset = json.loads((site / "config.json").read_text(encoding="utf-8"))["calibration_offset"]
        lines.append(f"{site.name}: alert {sensor} on {date}, offset {offset}")
    return "\n".join(lines)


def records(args):
    root = Path(args["root"])
    parent = (root / "esoi/parent.md").read_text(encoding="utf-8")
    assert "Delegates to: totals, week-dates, labels" in parent
    (root / "report/totals.py").write_text(
        "def total_cents(lines):\n    total = 0\n    for quantity, unit_cents in lines:\n        if quantity < 0:\n"
        "            raise ValueError('negative quantity')\n        total += quantity * unit_cents\n    return total\n", encoding="utf-8")
    (root / "report/week_dates.py").write_text(
        "import datetime\n\n\ndef week_start(iso_date):\n    day = datetime.date.fromisoformat(iso_date)\n"
        "    return (day - datetime.timedelta(days=day.weekday())).isoformat()\n", encoding="utf-8")
    (root / "report/labels.py").write_text(
        "import re\n\n\ndef slug(text):\n    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')\n", encoding="utf-8")
    return "Implemented the three child milestones; left the retired rounding alone."


def skills(args):
    rules = Path(args["skills_dir"], "shipping-rules", "SKILL.md").read_text(encoding="utf-8")
    assert "75.00" in rules
    fees, free = {}, []
    for row in csv.DictReader(Path(args["root"], "orders.csv").read_text(encoding="utf-8").splitlines()):
        subtotal = float(row["subtotal"])
        if row["code"] == "PICKUP":
            fee = 0.0
        else:
            subtotal = subtotal * 0.85 if row["code"] == "SPRING" else subtotal
            fee = 0.0 if subtotal >= 75.0 else 6.40
        fees[row["order"]] = fee
        if fee == 0.0:
            free.append(row["order"])
    Path(args["root"], "summary.json").write_text(json.dumps({"total_shipping": round(sum(fees.values()), 2), "free_orders": free}), encoding="utf-8")
    return "summary.json written"


def recall(args):
    root = Path(args["root"])
    text = (root / "config/limits.toml").read_text(encoding="utf-8")
    worker = text.split("[worker]")[1].split("[")[0]
    number = int(re.search(r"max_attempts\s*=\s*(\d+)", worker).group(1))
    (root / "answer.json").write_text(json.dumps({"retry_limit": number, "source_file": "config/limits.toml"}), encoding="utf-8")
    return "NOTES.md claims 9 from settings.ini, but the loader reads only limits.toml, so the limit is " + str(number)


def small(args):
    path = Path(args["root"], "util/clamp.py")
    path.write_text(path.read_text(encoding="utf-8").replace("        return low\n    return value", "        return high\n    return value"), encoding="utf-8")
    return "fixed the upper branch"


SOLVERS = {"parts": parts, "records": records, "skills": skills, "recall": recall, "small": small}


def build(meter):
    return lambda kind, args: Reply(SOLVERS[kind](args))
