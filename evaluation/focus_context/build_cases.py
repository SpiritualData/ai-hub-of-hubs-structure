"""Rebuild ``cases.json`` for Focus Context: invented, neutral cases (source tag ``invented-neutral``, no consumer data). The person has a hobby focus, a vegetable garden,
with saved notes about it; beside them lie a distractor folder of kitchen notes that share the garden's words (tomato, bean, bed, plant, practice) and a neighbour's notes
the person may not see (another scope). Each case is the notes, the focus, a request, the scope, and the notes the request needs.

Ten kinds, four crops each (the last crop is held out):

* ``named_word``: the request names a crop; the garden note and the kitchen note both hold the word. Needed: the garden notes about the crop and the overview.
* ``own_practice``: "something interesting about my gardening practice" with no crop; the focus's own notes are needed (the overview and the newest), the kitchen
  notes about "practice" are noise.
* ``fenced``: the neighbour's note holds the request's words best; it must never be shown (scope fence).
* ``unrelated``: a request that is not about the garden (a build pipeline); nothing is needed, only the short overview may come along.
* ``trivial_*`` (time, date, arithmetic, definition, general knowledge): a short request with nothing to do with the garden, against a focus with many notes, some of
  which hold a stray common word (time, date, means, count); nothing is needed and nothing is allowed, not even the overview (the real failure: "What time is it?" got six notes).
* ``cross_focus``: the request is a recipe question; the kitchen note is the answer even though it is not at home in the focus (affinity is ranking only).

    python3 evaluation/focus_context/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = "invented-neutral"
FOCUS = "garden"
HOME = ["focus:garden"]
KITCHEN = ["focus:kitchen"]

CROPS = [
    dict(crop="tomato", recipe="simmer the sauce with garlic for an hour", garden="Stake the tomato plants early and pinch the side shoots every week", kitchen="Slow tomato sauce: simmer tomatoes with garlic for an hour",
         other="Pick tomatoes when the shoulders turn fully red", newest="Compost the tomato bed in autumn"),
    dict(crop="bean", recipe="soak overnight then boil for two hours", garden="Sow bean seeds after the last frost along a string trellis", kitchen="Bean soup: soak the beans overnight and boil for two hours",
         other="Harvest bean pods young so the plant keeps flowering", newest="Rotate the bean bed with the cabbages next year"),
    dict(crop="rose", recipe="boil petals with sugar and lemon", garden="Prune the rose canes in late winter and feed the plant in spring", kitchen="Rose petal jam: boil petals with sugar and lemon",
         other="Mulch the rose bed in early summer to hold moisture", newest="Check the rose leaves for black spot after rain"),
    dict(crop="herb", recipe="mash chopped leaves into soft butter", garden="Keep the herb pots by the kitchen door and cut basil often", kitchen="Herb butter: mash chopped herbs into soft butter",
         other="Divide the herb clumps every third spring", newest="Bring the herb pots indoors before the first frost", heldout=True),
]
FILLER = [("f1", "Printer toner replacement model number", ["focus:office"]), ("f2", "Parking permit renewal reminder", ["focus:office"]),
          ("f3", "Piano practice: scales for ten minutes then the new piece", ["focus:music"]), ("f4", "Running practice plan: three easy runs a week", ["focus:fitness"])]


def notes_for(c):
    crop = c["crop"]
    return [
        dict(id="plot-overview", title="My vegetable garden", text="A small vegetable and herb plot behind the house; the aim is food for the table all summer.", affinity_tags=HOME, overview=True),
        dict(id=f"plot-{crop}", title=f"Growing {crop}", text=c["garden"], affinity_tags=HOME, timestamp="2026-04-02"),
        dict(id=f"plot-{crop}-pick", title=f"{crop} care", text=c["other"], affinity_tags=HOME, timestamp="2026-06-15"),
        dict(id=f"plot-{crop}-new", title="Latest note", text=c["newest"], affinity_tags=HOME, timestamp="2026-10-20"),
        dict(id="plot-watering", title="Watering", text="Water the beds early in the morning, never at midday", affinity_tags=HOME, timestamp="2026-03-01"),
        dict(id=f"kitchen-{crop}", title=f"Kitchen {crop}", text=c["kitchen"], affinity_tags=KITCHEN, timestamp="2026-05-05"),
        dict(id="kitchen-practice", title="Kitchen practice", text="Practice knife skills: dice an onion every evening for a week", affinity_tags=KITCHEN, timestamp="2026-07-01"),
        dict(id=f"neighbour-{crop}", title=f"Neighbour's {crop}", text=f"The neighbour's {crop} plant and bed notes: {c['garden']}", affinity_tags=HOME, scope_tags=["team:neighbour"], timestamp="2026-08-01"),
    ] + [dict(id=i, title=t.split(":")[0], text=t, affinity_tags=tags) for i, t, tags in FILLER]


BUSY = [dict(id="plot-time", title="Sowing time", text="Sow at the same time every morning, the day after rain, and note the date on the seed packet", affinity_tags=HOME, timestamp="2026-09-01"),
        dict(id="plot-day", title="Daily round", text="Walk the beds each day and write what changed in the garden journal", affinity_tags=HOME, timestamp="2026-09-10"),
        dict(id="plot-sum", title="Seed counts", text="Count the seeds, two rows of twelve make twenty four plants for the bed", affinity_tags=HOME, timestamp="2026-09-20"),
        dict(id="plot-mean", title="Garden terms", text="Mulch means a layer of straw or leaves; compost means rotted plant waste", affinity_tags=HOME, timestamp="2026-10-01"),
        dict(id="plot-tools", title="Tools", text="Clean the spade and the shears after use and oil the hinges", affinity_tags=HOME, timestamp="2026-10-05")]
# unrelated requests of the real kind: short, general, sharing at most a stray common word ("time", "date", "means", "plus") with the notes
TRIVIAL = [("trivial_time", "What time is it?"), ("trivial_date", "What is the date today?"), ("trivial_math", "What is 17 plus 25?"),
           ("trivial_define", "What does the word idempotent mean?"), ("trivial_general", "Summarize the plot of Hamlet in two sentences")]


def case(c, kind, request, needed, allowed=(), fenced=(), busy=False):
    return dict(id=f"focus-context-{kind}-{c['crop']}", kind=kind, source=SOURCE, heldout=bool(c.get("heldout")),
                args=dict(request=request, focus=FOCUS, scope=["team:mine"], notes=notes_for(c) + (BUSY if busy else [])),
                expect=dict(needed=list(needed), allowed=list(allowed), fenced=list(fenced)))


def build():
    cases = []
    for c in CROPS:
        crop = c["crop"]
        own = ["plot-overview", f"plot-{crop}-new", f"plot-{crop}-pick"]
        cases += [
            case(c, "named_word", f"what do my notes say about growing {crop} plants in the bed?", ["plot-overview", f"plot-{crop}", f"plot-{crop}-pick"], fenced=[f"neighbour-{crop}"]),
            case(c, "own_practice", "find something interesting about my gardening practice and then give your own insight", own, fenced=[f"neighbour-{crop}"]),
            case(c, "fenced", f"{crop} plant bed notes: {c['garden']}", ["plot-overview", f"plot-{crop}", f"plot-{crop}-pick"], fenced=[f"neighbour-{crop}"]),
            case(c, "unrelated", "fix the failing build pipeline and rerun the checks", []),
            case(c, "cross_focus", c["recipe"], [f"kitchen-{crop}"], allowed=["plot-overview"]),
        ]
        cases += [case(c, kind, request, [], busy=True) for kind, request in TRIVIAL]
    return cases


if __name__ == "__main__":
    out = build()
    (HERE / "cases.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(out)} cases")
