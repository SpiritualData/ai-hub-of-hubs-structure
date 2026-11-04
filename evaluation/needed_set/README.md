# needed-set: do the top cards bundle the files a piece of work needed?

Topic cards group the information on one topic from many files. This component judges a builder by that: a task reads as a topic
or an intent, the files the work touched are the needed set, and the card is the unit of retrieval. The file-finding component
(`cards_from_files`) judges a card per file by construction; this one does not.

## Cases and the split in time

- 150 tasks from the git history of Quest AI Runner: a commit that changed two to eight `quest_ai_runner/*.py` files whose subject
  is at least 30 characters and names nothing to look up (`cases.names_something`: no path, no `/`, no file name or extension, no
  snake_case, CamelCase or lowerCamelCase identifier, no `name()` call, no backticked text). The subject is the task; the changed
  files that are in the pinned corpus are the needed set (at least two).
- The cases are the 150 most recent such commits. Every older commit is the history a builder may learn from
  (`datasets/cochange_history.json`: subject and corpus files of 480 commits); no test commit is in it, and the history ends before
  the oldest test commit. `datasets/qar_commits_pin.json` holds the sha256 of both files, checked on every use (`CasesMismatch`);
  `cases.write` refuses to replace them unless told to.
- The corpus, the single build per run and the fixed selector (ten cards in view) are those of `cards_from_files`, shared through its
  `score` module.

## The rule

A case reads the first three cards of the view. It records `cov1` and `cov3` (the share of the needed files inside the first card and
inside the first three), `noise3` (the share of the files of those three cards that are not needed), and, for a task whose needed
files lie in more than one folder, `bundled` (one of the three cards holds needed files from two or more folders). A case passes when
`cov3` is at least one half and the three cards hold at most 30 distinct files, so one giant card cannot pass.

The store counts. `cards` and `cards_per_file` are in the details, and a builder with more than 0.25 cards per file is disqualified:
the run records a balanced score of zero. The Quest store keeps at most 1,000 cards, and a card per file is an index of files, not a
topic. The balanced score weighs accuracy, cost and time (`[balance.needed_set]`); its store-size term is this gate.

## Known limits

- Subjects are developer language written for a commit, and a few of the files were renamed or removed later (only files in the
  pinned corpus count).
- The corpus is the pinned state while the tasks are earlier, so a file that did not exist at the time of a task is still a needed
  file of it; a builder cannot be blamed for a file it could not have seen, and no builder is helped by it.
- A builder that learns from history sees only files that changed before the cut; the files created later are reachable only through
  its fallback cards.
- Coverage by cards is not an answer found: it says the right files were in front of the reader, not that the reader used them.

## Arms

The same declared arms as `cards_from_files` (none is copied): the topic builders `topic_cards_replay`, `cochange_topic_cards` and
`import_graph_topic_cards`, the floor `per_file_symbols` and `file_plus_topic_cards` (disqualified by the store cap), and the three
degenerate baselines in `impls/`. `llm_topic_cards` is listed under `paid_arms` and has no row here; `topic_cards_replay` is its saved
build.
