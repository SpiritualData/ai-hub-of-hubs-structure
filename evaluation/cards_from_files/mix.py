"""The one place that says how the three kinds of case are mixed into the single score of ``cards_from_files``.

``MIX`` gives each kind a weight; a kind's share of the case set is its weight over the weights' sum, and the file-finding kind (all of
its pinned cases) sets the unit, so with the weights below the set holds every file-finding case, as many orientation cases, and twice as
many topic cases. A later set of real inputs calibrates these numbers: change them here and nowhere else. They were fixed before any
arm was scored on the mixed set, by value: the topic kind is what topic cards are for, so it counts twice the file-finding kind (which a
card per file wins by construction) and the orientation proxy (nearness only).
"""
MIX = {"file": 1.0, "topic": 2.0, "orientation": 1.0}


def counts(pools):
    """``{kind: number of cases}`` from the size of each kind's pinned pool (a kind never takes more cases than its pool holds)."""
    unit = pools["file"] / MIX["file"]
    return {kind: min(pools[kind], round(unit * MIX[kind])) for kind in MIX}
