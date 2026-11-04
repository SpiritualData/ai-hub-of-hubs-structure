"""The one place that says which kinds of case make up the single score of ``context_retrieval``, and the fixed numbers of that score.

``MIX`` gives each kind a weight and a kind's share of the case set is its weight over the sum; the file-finding kind (all 63 pinned
cases) sets the unit, so the set holds every file-finding case, twice as many topic cases, half as many orientation cases and half as many
cases that need no context. The weights were fixed before any arm was scored, by value: the topic kind is what retrieval is for (a task
that needs several files), a file lookup is the easy case, orientation is a nearness proxy, and about one request in eight to a developer's
assistant needs nothing from the corpus (thanks, a general question), which is where an arm that always returns something pays in noise
tokens. When a sample of real requests exists, calibrate the counts here and nowhere else.

The accuracy of a case is its graded utility (``UTILITY``) in 0..1, and a case counts when that utility, after the store penalty, is above the
case's fixed place in [0, 1) (a hash of its id). The expected number counted is therefore the mean utility, which is how a fractional accuracy
enters esoi's pass count until the library carries one.
"""
MIX = {"file": 1.0, "topic": 2.0, "orientation": 0.5, "none": 0.5}
BUDGET_TOKENS = 4000          # what a task is shown: about two thirds of a long file
UTILITY = {"recall": 0.60, "ndcg": 0.25, "quiet": 0.15}   # recall of the needed text within the budget, graded nDCG@10, and 1 minus the noise share of the tokens shown
GAINS = {"needed": 2.0, "helpful": 1.0}
STORE_RATIO_LIMIT = 8.0       # an index this many times the corpus's size gives up every case
STORE_EXPONENT = 2.0


def counts(pools):
    unit = pools["file"] / MIX["file"]
    return {kind: min(pools[kind], round(unit * MIX[kind])) for kind in MIX}
