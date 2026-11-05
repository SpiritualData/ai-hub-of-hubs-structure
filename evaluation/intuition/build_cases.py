"""Rebuild cases.json for Intuition: invented neutral cases (source tag ``invented-neutral``, no consumer data), because the hub holds no consumer's record of what a
person kept. Each case is a small store of cards, a log of what was taken for earlier requests (``age_days`` ago), a request, a limit and the ids that are useful.

Four kinds, five domains each:

* ``wording``: the useful card shares words with the request (a similarity arm should find it).
* ``companion``: the useful card shares no word with the request, but it was taken for an earlier, similar request (only a log of takes can surface it).
* ``stale``: two cards were taken for similar earlier requests, one days ago and one months ago; only the recent one is useful (a take must fade).
* ``none``: nothing in the store bears on the request and the log is unrelated; the right answer is to offer nothing.

    python3 evaluation/intuition/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = "invented-neutral"

DOMAINS = [
    dict(name="garden", request="when should I prune the roses", earlier="how to prune roses before spring", wording="Prune roses in late winter before new growth starts",
         companion="Sharpen and oil the secateurs", other="Compost heap needs turning monthly", old="Order mulch for the vegetable beds"),
    dict(name="trip", request="plan the weekend trip", earlier="plan the weekend trip to the coast", wording="Weekend trip plan: ferry times and the coast hotel",
         companion="Packing list: passport, charger, rain jacket", other="Sourdough starter feeding schedule", old="Renew the travel insurance policy"),
    dict(name="budget", request="monthly budget review", earlier="monthly budget review with the spreadsheet", wording="Monthly budget review: compare spending with the plan",
         companion="Bank export steps: download the statement as csv", other="Bicycle chain needs lubricating", old="Cancel the unused gym subscription"),
    dict(name="sky", request="what is visible in the night sky tonight", earlier="night sky tonight which planets are visible", wording="Night sky tonight: Jupiter rises after nine",
         companion="Telescope eyepiece cleaning routine", other="Quarterly tax payment due dates", old="Star chart app settings for red light"),
    dict(name="chess", request="improve my chess endgames", earlier="improve chess endgames rook endings", wording="Chess endgames: king and pawn opposition drills",
         companion="Notebook of annotated rook positions", other="Boiler pressure should sit near one bar", old="Tournament registration form"),
]
FILLER = [("filler-1", "Printer toner replacement model number"), ("filler-2", "Office plant watering rota"), ("filler-3", "Parking permit renewal reminder")]


def store(domain, extra):
    cards = [("c-wording", domain["wording"]), ("c-companion", domain["companion"]), ("c-other", domain["other"]), ("c-old", domain["old"])] + FILLER
    return [{"id": i, "text": t} for i, t in cards if i in extra or i.startswith(("filler", "c-other"))]


def case(domain, kind, history, expect, request=None):
    keep = {"wording": ("c-wording",), "companion": ("c-companion",), "stale": ("c-companion", "c-old"), "none": ("c-companion",)}[kind]
    return {"id": f"intuition-{kind}-{domain['name']}", "kind": kind, "source": SOURCE,
            "args": {"request": request or domain["request"], "limit": 3, "cards": store(domain, keep), "history": history}, "expect": expect}


def main():
    cases = []
    for d in DOMAINS:
        cases.append(case(d, "wording", [], ["c-wording"]))
        cases.append(case(d, "companion", [{"request": d["earlier"], "taken": ["c-companion"], "age_days": 3}], ["c-companion"]))
        cases.append(case(d, "stale", [{"request": d["earlier"], "taken": ["c-companion"], "age_days": 2}, {"request": d["earlier"], "taken": ["c-old"], "age_days": 120}],
                          ["c-companion"]))
        cases.append(case(d, "none", [{"request": d["earlier"], "taken": ["c-companion"], "age_days": 5}], [], request="translate this invoice into French"))
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
