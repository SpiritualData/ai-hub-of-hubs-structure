# Adopt the hub

Use this when your application has jobs the hub already defines (prioritizing work, starting standing work, retrieving context, asking a person only when
they would want to be asked) and you want those jobs to stay the hub's, with your data and your arms added beside them. Quest AI Runner, the first adopter,
is described in [its README](https://github.com/SpiritualData/quest-ai-runner). The general form is esoi's
[adopt a solution from a library](https://github.com/SpiritualData/evolvable-structure/blob/main/docs/how-to/adopt-a-solution-from-a-library.md); this page
applies it to the hub. The code below is run by `tests/test_adopt_the_hub_how_to.py`, offline, so it cannot rot.

## 1. Decide for each of your solutions: adopted, specialized or own

Ask of each job: would a stranger's use of the hub need this?

- Yes: **adopt** it. Your records hold only the reference, your arms and your metrics.
- It needs your application's data: **specialize** it. Your record states what your data adds and points at the hub's solution.
- Only your application has it: **own** it, with full records as usual.

An own solution that turns out to be general is proposed back to the hub as a solution record with its problems and ideals. Once the hub has it, your record
becomes an adopted one and your code moves in as an arm.

## 2. Declare the hub and the adoption

Name the hub in `esoi.toml`, then add one row to the `solutions.csv` where the solution belongs. The reference is `@hub/<solution id>`; leave every field the
hub defines empty. This example builds a small application, adopts one solution, specializes it and mistypes a third id on purpose:

```python
import pathlib
import subprocess
import sys
import tempfile

import hubofhubs
from esoi import implementation
from hubofhubs.api import Binding, assemble, evaluate, register

hub = pathlib.Path(hubofhubs.__file__).resolve().parent.parent       # the hub's repository, beside yours when you work from a checkout
app = pathlib.Path(tempfile.mkdtemp())
(app / "esoi").mkdir()
(app / "esoi.toml").write_text(f'package = "notes_app"\nlayers = ["core"]\n[adopts.hub]\nrepo = "{hub}"\n[records]\ntemplate_version = 4\n')
(app / "esoi" / "solutions.csv").write_text(
    "solution_id,name,adopts,specializes\n"
    "prioritization,Prioritization,@hub/prioritization,\n"               # adopted: the hub's words are shown on the page
    "prioritize-notes,Prioritize notes,,@hub/prioritization\n"           # specialized: needs this application's data
    "note-search,Note Search,@hub/no-such-solution,\n")                  # a mistyped id, so the check says so
checked = subprocess.run([sys.executable, "-m", "esoi", "check", "--findings"], cwd=app, capture_output=True, text=True)
print([line.strip().split(";")[0] for line in checked.stdout.splitlines() if line.strip().startswith("S53")])
```

It prints the one adoption finding: `note-search` names a hub solution that does not exist. The adopted and the specialized rows resolve and raise nothing.

## 3. Pass your Binding, call parts by id or typed handle

Your application hands the hub a `Binding` (its name, its repository, its seats, where its records are, which implementation names its code declares) and the
hub never imports you. Everything you call comes from `hubofhubs.api`; never import a path inside the hub, because parts move.

```python
binding = Binding(consumer="notes-app", root=app, seats=[], core_dir=app, records_dir=app / "esoi", names_of=lambda solution_id: [])
facts, wired, numbers = evaluate(binding)
print("clean_share" in numbers)
print(hubofhubs.run("prioritization", {"candidates": [{"id": "n1"}]})["ordered"][0]["id"])     # by id; the typed handle is hubofhubs.run(Prioritizing)
```

It prints `True` and then `n1`: the score of your integration is read from your records and code, and the part answers with the arm the hub's metric selected.

## 4. Add your own arm, and build your metric on the hub's

Your arm of an adopted solution declares the hub's solution id and follows its interface, so the hub's seat reaches it. It competes under the hub's metric on
the hub's cases:

```python
@implementation("prioritization", "newest-first")      # the hub's solution id, then your arm's name
class NewestFirst:
    REQUIRES = ()

    def prioritize(self, person="", request="", implied=None, candidates=(), stated=None, now=""):
        order = sorted(candidates, key=lambda c: c.get("asked_at", ""), reverse=True)
        return {"ordered": [{"id": c["id"], "rank": n, "reason": "asked most recently"} for n, c in enumerate(order, 1)],
                "held": [], "quality_weights": {}, "constraints": []}


register("prioritization", "newest-first", NewestFirst)
notes = [{"id": "n1", "asked_at": "2026-07-01T00:00:00Z"}, {"id": "n2", "asked_at": "2026-07-09T00:00:00Z"}]
mine = assemble(hubofhubs.AssemblyConfig(solutions=("prioritization",), selections={"prioritization": "newest-first"}))
print([i["id"] for i in mine["prioritization"].prioritize(candidates=notes)["ordered"]])
```

It prints `['n2', 'n1']`. List the arm in the `implementations` cell of your adopted row and give it a row in `implementations.csv` whose `solution_id` is the
adopted solution. Your application's metric then builds on the hub's with a `[builds_on]` table in your `esoi.toml`, so your arm is scored on the hub's cases plus
only the cases that are your own, in one number, and nothing of the hub's is copied ([why](https://github.com/SpiritualData/evolvable-structure/blob/main/docs/explanation/a-metric-builds-on-its-foundation.md)):

```toml
[builds_on.note_ordering.hub_cases]
repo = "../ai-hub-of-hubs-structure"
component = "prioritization"
share = 0.5            # the hub's cases carry half of your one number; your own cases carry the rest
```

## 5. What the checks tell you, and overriding only what differs

`esoi check --findings` runs rule S53 and informs, never fails. It names an adoption that does not resolve, an adopted row that restates what the hub says
(empty those cells), an own solution that says the same job as a hub solution (adopt or specialize it, or waive it with the reason the job differs in
`waivers.csv`) and an arm that does not declare the hub's solution id. Each finding says its next action.

Every call keeps the hub's default for what you do not name. Override only what differs, as in section 4: `arms={...}` or `selections`, `options={...}`,
`provided={...}`, a lock file. A better hub arm that wins its metric then reaches you with no change of yours.

```python
default = assemble(hubofhubs.AssemblyConfig(solutions=("prioritization",)))
print([i["id"] for i in default["prioritization"].prioritize(candidates=notes)["ordered"]])
```

It prints `['n1', 'n2']`: with no selection of yours, the hub's own arm keeps the order given.

## 6. An autopilot

Adopt Proactivity and Prioritization and write only what is yours: your events as an Intake Sources adapter, and your priorities as the Representative's
preferences. Nothing else needs a hub change. The loop, with a runnable example, is in [build an autopilot on the hub](build-an-autopilot-on-the-hub.md).
