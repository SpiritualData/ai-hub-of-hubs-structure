# cards-from-files: one number for what a builder's cards do for a reader

A card groups information on one topic from many files. A card per file is an index of files, a different thing, so it is a
baseline here and never a builder to ship. This component gives every builder one balanced score, from one case set that mixes three
kinds of case; the kinds are case sources of that one number, not separate leaderboards.

## Cases and corpus

- The corpus is every `.py` file of Quest AI Runner at the commit named in `datasets/qar_pin.json` (its `evaluation` folder left
  out) followed by the `.py` files of the `hubofhubs` package at the pinned hub commit: 892 files, in walk order. `corpus.py` reads
  both with `git archive` into a cached temporary folder and never touches a working tree; it checks the pinned sha256 of the cases
  file and of the sorted file list on every use (a mismatch is an error). The checkouts are found from `CARDS_FROM_FILES_QAR_REPO`
  and `CARDS_FROM_FILES_HUB_REPO`, then the sibling folder `quest-ai-runner` and this repository, then a clone of the pinned URL.
- Three kinds, mixed with the weights of `mix.py` (the one place to change them; a later set of real inputs calibrates them):
  - `file`: 63 file-finding tasks with one needed file each, the cases of Quest AI Runner's context-selection component at the pinned
    commit. Right when the needed file is among the first three files of the view. A card per file wins this kind by construction.
  - `topic` (`topic_cases.py`, `topic_kind.py`): subjects of Quest AI Runner's git history that name no path, file name, extension,
    code identifier or backticked text (deterministic regular expressions), for commits that changed two to eight package files; the
    files changed that are in the corpus (at least two) are the needed set. Right when at least half of them are inside the first
    three cards and those cards hold at most 30 files. The details give the share inside the first card and the first three, the
    noise (files shown that were not needed) and how often a card bundled files of two folders when the task spans them.
  - `orientation` (`orientation_kind.py`): the file-finding tasks again, right when a file of the target's own folder is among the
    first three files; `area_hit` records whether the first card's common folder is the target's folder or its parent. A proxy for
    nearness, free and with no model.
- The topic cases are cut in time: the 150 most recent qualifying commits are the pool, and every older commit is the history a
  builder may learn from (`datasets/topic_cases/cochange_history.json`); no test commit is in it. `datasets/topic_cases/qar_commits_pin.json`
  holds the sha256 of both files, checked on every use (`CasesMismatch`); `topic_cases.write` refuses to replace them unless told to.
  With the weights in `mix.py` the set holds the 63 file cases, 63 orientation cases and 126 topic cases.

Known limits: topic subjects are developer language written for a commit, and some files were renamed or removed later (only files in
the pinned corpus count); the corpus is the pinned state while the topic tasks are earlier, so a file that did not exist at the time is
still a needed file and a history-learning builder cannot have seen it; coverage is the right files in front of the reader, not an
answer found; the selector is keyword IDF, not production's hybrid.

## The rule

1. The builder is called once, on the first case, with the corpus root, the files in walk order and no existing cards. Its model
   calls, tokens, cost and seconds are charged to that case, because one build serves every case of a run.
2. The fixed selector is Quest AI Runner's keyword IDF card store at the pinned commit (confidence gate off, ten cards in view).
3. The view is the picked cards in rank order, each card's files in the order the builder listed them. Nothing reorders a card's
   files per query, as in production.
4. A case is counted when it is right for its kind and its fixed place in [0, 1) (a hash of its id) is at or above the store penalty:
   the square of the cards per file, one when the cards exceed the 1,000 a Quest store holds. A card per file scores nothing and a
   topic store of a tenth of the files loses about one case in a hundred. The balanced score weighs the counted accuracy, cost and
   time by `[balance.cards_from_files]` in `esoi.toml`, whose weights were fixed before any arm was scored on the mix.
   The details give each kind's raw and counted results, the store, the topic numbers and the build.

A builder that puts many files in one card pushes the needed file past the third position and fills the view, so `broken/` holds three
degenerate builders (every file in one card, two cards, one card per folder) that must be right on no topic case; `tests/test_topic_cards.py`
proves it on the real corpus, and proves that a card per file, right on many cases, counts none.

## Arms

| Arm | What it is | Cost |
|---|---|---|
| `per_file_symbols` | BASELINE (a floor for finding a file, never a card builder): one card per file, from its docstrings and symbols | none |
| `graphify_files` | one card per community of Graphify's file graph, files ordered by connection (code-only extraction, no model) | none |
| `llm_topic_cards` | topic cards a model writes from sampled files, duplicates merged | model calls on every build; listed in `paid_arms` |
| `topic_cards_replay` | the 103 topic cards of the one paid `llm_topic_cards` build (id 75f9da90), replayed from `datasets/replays/` | none |
| `file_plus_topic_cards` | `per_file_symbols` cards plus those topic cards (ids prefixed `topic-`); keeps a card per file, so the store term takes its score | none |
| `cochange_topic_cards`, `import_graph_topic_cards` | topic cards grouped from the co-change history or the import graph, no model (`hubofhubs/recall/cards_from_topics.py`) | none |
| `one_card`, `two_cards`, `one_card_per_folder` | baselines, see above | none |

The paid build is persisted once, so it is never bought again for the same code: `datasets/replays/llm_topic_cards_75f9da90.json`
holds the cards, the pin they were built on (a replay on any other corpus is refused), the build's calls, tokens and cost
(52 calls, 93,660 tokens, $0.9967), and a sha256 of the cards that is checked on every load. The cards name 140 file entries over 102
distinct files of the 892. The build's id was 75f9da90 when the harness computed it in the paid run; the card order of that run was not
kept, so the stored cards in their recovered order have id b5107a67, and that is the id a replay records. Each card's local
`origin` field was dropped. A replay's row carries the original build's calls and cost in its details as "replayed from build
75f9da90"; its own cost is zero. On the file-finding cases it scores what the paid build scored: `topic_cards_replay` 5 of 63 (the paid run's 5 of 63,
reproduced exactly), `file_plus_topic_cards` 40 of 63, below the per-file floor's 43, so the topic cards do not help the floor here.

`graphify_files` needs the `graphify` extra (`pip install "hubofhubs[graphify]"`), so it runs in an environment that has it:

    python3 -m esoi run cards_from_files --impl graphify_files --record

Results are in `esoi/results.csv`; the leaderboard (`python3 -m esoi leaderboard`) lists an arm with no recorded row as not measured.
