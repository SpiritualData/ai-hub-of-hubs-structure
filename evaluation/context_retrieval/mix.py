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
MIX = {"file": 1.0, "topic": 2.0, "orientation": 0.5, "none": 0.5, "memory": 0.75, "topic_open": 1.0, "grouping": 0.5}
# The three kinds added in November 2026 (shares fixed here and committed before any arm was scored on them, by value):
#   memory     0.75: a long-term conversational memory (public benchmark, timestamped sessions; a newer fact supersedes an older one, facts
#                    lie across sessions, some questions have no answer in the history): a distinct need, but one benchmark's style, so less than topic.
#   topic_open 1.0:  topic requests like ``topic`` over two other public Python repositories read at pinned commits, so a method that fits one
#                    codebase alone stops looking good; the request's focus is the repository the commit belongs to.
#   grouping   0.5:  the same kind of request, but the request's focus is the sibling repository and the needed files lie in the other one
#                    (the item's home is not the request's focus): a soft preference for the focus against a hard fence.
# The pools hold exactly these counts (memory 47, topic_open 63, grouping 32): a test fails when a pool is smaller or larger than its share.
KIND_TOLERANCE = 0.05         # the gate on kinds (see README): an arm that leads the balanced score but trails the held arm on any kind by more than this much mean utility does not pass a stage
MIN_CASES = {"memory": 40, "topic_open": 50, "grouping": 25}   # a stage counts a new kind only when its case set holds at least this many
BUDGET_TOKENS = 4000          # what a task is shown: about two thirds of a long file
UTILITY = {"recall": 0.60, "ndcg": 0.25, "quiet": 0.15}   # recall of the needed text within the budget, graded nDCG@10, and 1 minus the noise share of the tokens shown
GAINS = {"needed": 2.0, "helpful": 1.0}
STORE_RATIO_LIMIT = 8.0       # an index this many times the corpus's size gives up every case
STORE_EXPONENT = 2.0


def counts(pools):
    unit = pools["file"] / MIX["file"]
    return {kind: min(pools[kind], round(unit * MIX[kind])) for kind in MIX if kind in pools}


# ---- source access: cost and risk of reading the sources at request time (fixed before any arm was scored on it) ------------------------------
# An arm answers from the index it built beforehand; reading the live sources while answering (scanning a server, many API calls) costs money, time
# and exposure even when it is accurate. The corpus hands every arm a ``SourceMeter`` (hubofhubs.retrieval.base) that counts, per request, the source
# calls, the records and the bytes read; an arm that reads only its prebuilt index counts 0. The count is folded into the case's cost at these prices
# (the balanced weights do not change):
SOURCE_CALL_USD = 0.0005      # one round trip to a source (an API request, a file open on a remote share): a tenth of the half-cent request budget
SOURCE_RECORD_USD = 0.00001   # one record read (a file, a message, a row), the per-item charge of a metered API
SOURCE_MB_USD = 0.0005        # one megabyte transferred from a source
# Risk gates (conditions a stage checks with evaluation/context_retrieval/gate.py, not weights):
MAX_SOURCE_CALLS = 20         # source calls in any one request (a handful of lookups is a retrieval, hundreds is a scan)
MAX_SCAN_SHARE = 0.05         # a request that reads more than this share of the records of the corpus is a full scan
MAX_OUT_OF_SCOPE = 0          # records read, or returned, outside the scope the request is allowed (scope_tags fence)
