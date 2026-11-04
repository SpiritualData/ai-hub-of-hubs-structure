# cards-from-files: does the needed file appear among the first three files a builder's cards show?

A builder proposes cards for the files of a folder. This component judges the cards by what they do for a reader: a fixed selector
ranks them for a task, shows the best ten, and the case passes when the file the task needs is among the first three files of what
is shown.

## Cases and corpus

- 63 file-finding tasks, each with the one file that answers it: the cases of Quest AI Runner's context-selection component at the
  commit named in `datasets/qar_pin.json`. Four of the targets are files of this package.
- The corpus is every `.py` file of Quest AI Runner at that commit (its `evaluation` folder left out) followed by the `.py` files of
  the `hubofhubs` package at the pinned hub commit: 892 files, in walk order.
- `corpus.py` reads both with `git archive` into a cached temporary folder and never touches a working tree. It checks the pinned
  sha256 of the cases file and of the sorted file list on every use; a mismatch is an error. The checkouts are found from
  `CARDS_FROM_FILES_QAR_REPO` and `CARDS_FROM_FILES_HUB_REPO`, then the sibling folder `quest-ai-runner` and this repository, then a
  clone of the pinned repository URL.

## The rule

1. The builder is called once, on the first case, with the corpus root, the files in walk order and no existing cards. Its model
   calls, tokens, cost and seconds are charged to that case, because one build serves every case of a run.
2. The fixed selector is Quest AI Runner's keyword IDF card store at the pinned commit (confidence gate off, ten cards in view).
3. The view is the picked cards in rank order, each card's files in the order the builder listed them. Nothing reorders a card's
   files per query, as in production.
4. A case passes when the needed file is within the first three files of the view. The details also give the first ten files, the
   needed file anywhere in the view, the median and largest view, the cards built, the build's id, and its calls, tokens, cost and
   seconds. The balanced score weighs accuracy, cost and time by `[balance.cards_from_files]` in `esoi.toml`.

A builder that puts many files in one card pushes the needed file past the third position, so `broken/` holds three degenerate
builders (every file in one card, two cards, one card per folder) that must pass no case; `tests/test_cards_from_files.py` proves it
on the real corpus.

## Arms

| Arm | What it is | Cost |
|---|---|---|
| `per_file_symbols` | one card per file, from its docstrings and symbols | none |
| `graphify_files` | one card per community of Graphify's file graph, files ordered by connection (code-only extraction, no model) | none |
| `llm_topic_cards` | topic cards a model writes from sampled files, duplicates merged | model calls on every build; listed in `paid_arms` |
| `topic_cards_replay` | the 103 topic cards of the one paid `llm_topic_cards` build (id 75f9da90), replayed from `datasets/replays/` | none |
| `file_plus_topic_cards` | `per_file_symbols` cards plus those topic cards (ids prefixed `topic-`) | none |
| `one_card`, `two_cards`, `one_card_per_folder` | baselines, see above | none |

The paid build is persisted once, so it is never bought again for the same code: `datasets/replays/llm_topic_cards_75f9da90.json`
holds the cards, the pin they were built on (a replay on any other corpus is refused), the build's calls, tokens and cost
(52 calls, 93,660 tokens, $0.9967), and a sha256 of the cards that is checked on every load. The cards name 140 file entries over 102
distinct files of the 892. The build's id was 75f9da90 when the harness computed it in the paid run; the card order of that run was not
kept, so the stored cards in their recovered order have id b5107a67, and that is the id a replay records. Each card's local
`origin` field was dropped. A replay's row carries the original build's calls and cost in its details as "replayed from build
75f9da90"; its own cost is zero. It scores what the paid build scored: `topic_cards_replay` 5 of 63 (the paid run's 5 of 63,
reproduced exactly), `file_plus_topic_cards` 40 of 63, below the per-file floor's 43, so the topic cards do not help the floor here.

`graphify_files` needs the `graphify` extra (`pip install "hubofhubs[graphify]"`), so it runs in an environment that has it:

    python3 -m esoi run cards_from_files --impl graphify_files --record

Results are in `esoi/results.csv`; the leaderboard (`python3 -m esoi leaderboard`) lists an arm with no recorded row as not measured.
