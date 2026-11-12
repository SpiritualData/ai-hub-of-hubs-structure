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


def context(args):
    """Reads every document of every depot, keeps the latest adopted amendment of each rule."""
    lines = []
    for depot in sorted(Path(args["root"], "depots").iterdir()):
        current = {}
        for path in sorted(depot.glob("doc_*.md")):
            text = path.read_text(encoding="utf-8")
            date = re.search(r"^Date: (\S+)", text, re.M).group(1)
            if re.search(r"^Status: (\S+)", text, re.M).group(1) != "adopted":
                continue
            for kind, pattern in (("cutoff", r"cutoff (?:is|becomes) (\d+:\d+)"), ("lot", r"reorder lot (?:is|becomes) (lot-\d+)")):
                found = re.search(pattern, text)
                if found and (kind not in current or date > current[kind][0]):
                    current[kind] = (date, found.group(1))
        lines.append(f"{depot.name}: cutoff {current['cutoff'][1]}, reorder {current['lot'][1]}")
    return "\n".join(lines)


def two_level(args):
    root = Path(args["root"])
    (root / "shop/pricing.py").write_text(
        "def discounted(cents, percent):\n    if percent < 0 or percent > 100:\n        raise ValueError('percent')\n    return (cents * (100 - percent) + 50) // 100\n", encoding="utf-8")
    (root / "shop/order_totals.py").write_text(
        "from shop.pricing import discounted\n\n\ndef order_total(lines):\n    return sum(discounted(q * unit, pct) for q, unit, pct in lines)\n", encoding="utf-8")
    (root / "shop/labels.py").write_text("import re\n\n\ndef slug(text):\n    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')\n", encoding="utf-8")
    (root / "shop/orders.py").write_text(
        "from shop.order_totals import order_total\nfrom shop.shipping import shipping_cents\n\n\ndef order_summary(lines, weight_grams, zone):\n"
        "    return order_total(lines) + shipping_cents(weight_grams, zone)\n", encoding="utf-8")
    (root / "shop/report.py").write_text(
        "from shop.labels import slug\nfrom shop.orders import order_summary\n\n\ndef build_report(name, lines, weight_grams, zone):\n"
        "    return {'label': slug(name), 'total_cents': order_summary(lines, weight_grams, zone)}\n", encoding="utf-8")
    return ("shipping-fees needs data/carrier_rates.csv, which was never delivered, so it stays unimplemented.\n"
            "pricing: met\norder-totals: met\nlabels: met\nshipping-fees: unmet\norders: unmet\nshop-report: unmet")


def verify(args):
    root = Path(args["root"])
    totals = {}
    for name in ("january", "february", "march"):
        rows = (root / f"visits/{name}.csv").read_text(encoding="utf-8").splitlines()[1:]
        totals[name] = [int(r.split(",")[1]) for r in rows]
    week, fixed = re.search(r"week (\d+).*?true count is (\d+)", (root / "visits/corrections.md").read_text(encoding="utf-8"), re.S).groups()
    totals["february"][int(week) - 1] = int(fixed)
    sums = {k: sum(v) for k, v in totals.items()}
    best = max(sums, key=sums.get)
    total = sum(sums.values())
    (root / "summary.md").write_text(
        f"# Quarter summary\n\nTotal visits: {total:,} (visits/january.csv, visits/february.csv, visits/march.csv, with visits/corrections.md applied).\n"
        f"Best month: {best.capitalize()} (visits/{best}.csv).\n"
        "The recap differs from the files: it counted the double-counted February week, so its total is too high and it names the wrong best month.\n"
        "The recap's claim about the newsletter has no source in the folder, so it is left out as unverified.\n", encoding="utf-8")
    return "summary.md written"


def small_lookup(args):
    for path in sorted(Path(args["root"], "notes").glob("note_*.txt")):
        found = re.search(r"spare key is kept in locker (\d+)", path.read_text(encoding="utf-8"))
        if found:
            Path(args["root"], "answer.json").write_text(json.dumps({"note": path.name, "locker": int(found.group(1))}), encoding="utf-8")
    return "answer.json written"


SOLVERS = {"parts": parts, "records": records, "skills": skills, "recall": recall, "small": small, "context": context, "records-two-level": two_level, "verify": verify,
           "small-lookup": small_lookup}


def build(meter):
    return lambda kind, args: Reply(SOLVERS[kind](args))
