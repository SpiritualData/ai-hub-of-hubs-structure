# context_retrieval

Which retrieval arm shows a task the context it needs and little else? One component, one number: the arms of the `retrieve-context` seat
(`hubofhubs/retrieval`) are compared on the same corpus, the same token budget and the same requests, and every arm competes (no arm is
excluded by a mark; the weakest ones are diagnostic bounds that show what a method adds).

- **Corpus (the main world)**: every `.py` file of the consumer runner and the hub at the pinned commits of `cards_from_files/datasets/qar_pin.json` (892 files,
  read with `git archive`, the same pin the card builders are measured on). Arms cut it into about 13,000 units at natural boundaries
  (a header, each top-level function or class, a long class by method); `bm25_whole_files` keeps whole files.
- **Case sources** (`mix.py`, never separate stages or leaderboards): `file` (63 file-finding tasks), `topic` (150 commit subjects that name
  no file or identifier, newer than every commit of the history an arm may learn from; the files a commit changed are the needed set),
  `orientation` (the file tasks asked for a neighbourhood: a file of the target's folder in the first three), `none` (32 scored requests in
  `datasets/no_context.json` that need nothing from the corpus), and three kinds added in November 2026 whose shares were committed before any
  arm was scored on them (commit `38d2117`): `memory`, `topic_open` and `grouping`. The shares are 63 : 126 : 32 : 32 : 47 : 63 : 32 (395 cases).
  - `memory` (47): questions about a user's timestamped, multi-session chat history, a sample of **LongMemEval** (Wu et al., ICLR 2025; MIT licence,
    so the sample is committed in `datasets/memory/` with `LICENSE-LongMemEval.txt`; `pin.json` names the upstream revision and the sha256 of the
    277 MB file it was drawn from and the sha256 of the sample). Ten knowledge-update, ten temporal-reasoning, nine multi-session, eleven single-session
    questions and seven whose answer was never said (abstention); each history is its evidence sessions plus ten other sessions. Every chat turn is
    an item. The evidence turns are needed; the rest of a needed session is helpful; in a knowledge-update question the evidence turns of the older
    session are the superseded fact and count as irrelevant, so an arm that prefers the newer fact gains and one that returns both pays noise; an
    abstention question needs nothing and is scored like `none`. `memory.py` builds the sample (`python3 evaluation/context_retrieval/memory.py FILE`).
  - `topic_open` (63) and `grouping` (32): the same kind of topic request over three public Python repositories (httpx, httpcore, starlette; BSD-3-Clause)
    read with `git archive` at the commits of `datasets/open_code/pin.json` into the cache folder, never vendored (the pin holds each licence file's
    sha256 and the sha256 of the sorted file list). The 95 newest topic commits of the three are the cases and every older commit is the history an arm
    may learn from (321 commits), so the split in time is global. The request's *focus* is the repository the commit belongs to in `topic_open`; in
    `grouping` it is the sibling repository (httpcore for httpx, httpx for httpcore and starlette), so the needed files are at home elsewhere than the
    focus: a hard fence over the focus cannot answer them and a soft preference can. `open_code.py` builds the cases.
- **Item metadata and the request** (all optional, `hubofhubs.retrieval.units.ITEM_META`): an item may carry `kind` (message, note, file, commit,
  record_field), `author_role` (requester, other_person, assistant, system), `timestamp`, `affinity_tags` (its home groupings, `repo:httpx`) and
  `scope_tags`; a request may carry its `timestamp`, its focus (`affinity_tags`) and the `scope_tags` it may read. An arm that ignores them ranks
  exactly as before (a test checks it). They are filled from the benchmark's timestamps and roles for memory, and for code from the history (the date of
  the last commit of the history that changed a file, never a later one; its repository as home). `abstaining_recency`, `abstaining_affinity`,
  `abstaining_aware` and `abstaining_fenced` (the hard fence, for comparison) read them; all are free, and their constants were written before scoring.
- **Cost and risk of reading the sources** (`mix.SOURCE_*`, `mix.MAX_*`, fixed in commit `cfedeb1` before scoring): every arm owns a `SourceMeter`
  (`base.py`) that counts, per request, source calls, records and bytes read. An arm that answers from the index it built beforehand reads nothing and
  pays nothing; one that scans the sources per request pays per call (0.0005 USD, a tenth of the half-cent request budget), per record (0.00001) and per
  megabyte (0.0005), added to the case's cost, so the balanced weights do not change. `live_scan` (no index, every request reads every file) is the
  diagnostic bound that shows the charge. Risk is inside the one number: a request that makes more than `mix.MAX_SOURCE_CALLS` source calls, reads more than `mix.MAX_SCAN_SHARE` of a corpus or reads outside its scope gives up that case.
- **Bootstrapping is not an arm's job.** Building and refreshing the store from the sources belongs to the card-builder solution and its metric
  (`evaluation/cards_from_files`, which reports a build's source opens, files and megabytes, reads per item ingested, and for a free builder the reads of a
  refresh over the unchanged corpus against the full build, `refresh_share`). What stays with an arm is the index derived for that one method (its
  postings, vectors), charged here as the store-size term and the build seconds, which land on the first case of each world.
- **Graded labels**: a file is needed (the target, or a file the commit changed), helpful (it imports or is imported by a needed file) or
  irrelevant. A request is answered with units best first within 4,000 tokens.
- **Utility of a case** (`mix.UTILITY`, fixed before any arm was scored): 0.60 recall of the needed files among the units returned, 0.25 graded
  nDCG@10 (gain 2 needed, 1 helpful) and 0.15 times one minus the share of tokens shown that belong to irrelevant files. A request that needs no
  context scores one for returning nothing and loses the share of the budget it filled. An arm that returns nothing for a request that needs
  context scores zero.
- **Store size**: an index (postings, vectors) larger than the corpus gives up that share of every case: `(index bytes / corpus bytes / 8) ** 2`.
- **One number**: the library counts a case when it is right, so a case counts when its utility after the store penalty is above its fixed place
  in [0, 1) (a hash of its id); the expected count is the mean utility. The balanced score then weighs accuracy 0.70, cost 0.15 (budget half a
  cent a request) and time 0.15 (budget two seconds a request) by `[balance.context_retrieval]` in `esoi.toml`. The details give each kind's
  mean utility, recall, nDCG, noise, units, index size and the build seconds (charged to the first case).
- **Learning is split in time**: the learned reranker trains on `cochange_history.json` (480 commits older than every test case); the abstention
  floor is set by `calibrate.py` on the newest 100 of those commits and on `datasets/no_context_validation.json`, and no scored case is read there.
  A consumer trains the same arm on its private labels by passing them as `history`; nothing private is read here.
- **Free and cached**: no arm calls a model, but the dense arms embed the units once with the local `bge-small` model (cached by text in the
  system temporary folder; a cold build of about 13,000 chunks is a few minutes, a cached run seconds). The model reranker `llm_rerank` is paid,
  needs `--cassette DIR` to record and replay, and has not been run.
- **Run** (the dense and learned arms need `numpy`, `scikit-learn` and `fastembed`; set `CARDS_FROM_FILES_CACHE` and `TMPDIR` to a writable folder; `OPEN_CODE_<NAME>_REPO` may point at checkouts of the three repositories, else they are cloned into the cache): `PYTHONPATH=.:evaluation:../evolvable-structure/implementations/python ESOI_OFFLINE=1 python3 -m esoi run context_retrieval --impl hybrid_rrf --keep-going`
  (add `--record` to log it).
- **Measured on the 395-case mix** (2026-11-04, free arms; mean utility per kind; the 253-case numbers before the three kinds are in the earlier
  rows of `esoi/results.csv`, and the four old kinds score the same as before):

  | arm | balanced | file | topic | orient. | none | topic_open | grouping | memory |
  |---|---|---|---|---|---|---|---|---|
  | bm25_body | 0.658 | .69 | .47 | .58 | .04 | .37 | .49 | .71 |
  | bm25_fielded | 0.630 | .75 | .39 | .64 | .03 | .27 | .37 | .71 |
  | hybrid_rrf | 0.596 | .77 | .41 | .65 | .00 | .32 | .38 | .74 |
  | feature_rerank | 0.596 | .79 | .41 | .71 | .00 | .34 | .43 | .76 |
  | abstaining_hybrid (selected before) | 0.591 | .71 | .35 | .62 | .91 | .19 | .25 | .52 |
  | abstaining_affinity | 0.589 | .71 | .35 | .62 | .91 | .19 | .25 | .52 |
  | abstaining_recency | 0.588 | .71 | .35 | .62 | .91 | .18 | .24 | .52 |
  | abstaining_aware | 0.588 | .70 | .34 | .62 | .91 | .19 | .23 | .50 |
  | abstaining_fenced (hard fence) | 0.581 | .71 | .35 | .62 | .91 | .20 | 0.00 | .52 |
  | learned_rerank / abstaining_learned | 0.548 / 0.549 | | | | | | | |
  | dense_bge_small | 0.460 (build seconds on 47 memory worlds) | .71 | .38 | .71 | .00 | .31 | .37 | .75 |
  | live_scan (reads every source per request) | 0.196 (about $0.33 a request) | .17 | .12 | .10 | .27 | .13 | .14 | .63 |

  What it shows: the abstention floor was set on code requests and silences most temporal-reasoning memory questions (0.19 against 0.95 for the
  hybrid), so on the broader mix `abstaining_hybrid` is beaten by `bm25_body`, `bm25_fielded`, `hybrid_rrf` and `feature_rerank` (esoi leaderboard);
  the recency, affinity and supersession arms move knowledge-update memory (0.80 to 0.83 for `abstaining_aware`) and `topic_open` by a few hundredths but
  lose elsewhere, the hard fence scores 0 on `grouping` where the soft arms keep their score, and `live_scan` gives up cases on the source limits.
- **One number, no gates.** The stages of `metric-retrieve-context` compare arms on the balanced score alone. Risk (source calls, full scans, reads outside the scope) is a limit inside each case's score, the kinds count by the weights of `mix.MIX`, and the pins are checked by the case loaders.
- **Limits**: one benchmark of chat memory (English, one style, sessions as turns) and four Python repositories with commit-subject wording; the mix is set by value and a sample of real requests should calibrate it; file
  labels stand for relevance, so the right passage inside a needed file is not told from the rest; the cold embedding time is not in the seconds
  per request.
