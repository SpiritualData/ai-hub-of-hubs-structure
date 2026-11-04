# context_retrieval

Which retrieval arm shows a task the context it needs and little else? One component, one number: the arms of the `retrieve-context` seat
(`hubofhubs/retrieval`) are compared on the same corpus, the same token budget and the same requests, and every arm competes (no arm is
excluded by a mark; the weakest ones are diagnostic bounds that show what a method adds).

- **Corpus**: every `.py` file of Quest AI Runner and the hub at the pinned commits of `cards_from_files/datasets/qar_pin.json` (892 files,
  read with `git archive`, the same pin the card builders are measured on). Arms cut it into about 13,000 units at natural boundaries
  (a header, each top-level function or class, a long class by method); `bm25_whole_files` keeps whole files.
- **Case sources** (`mix.py`, never separate stages or leaderboards): `file` (the 63 file-finding tasks), `topic` (150 commit subjects that name
  no file or identifier, newer than every commit of the history an arm may learn from; the files a commit changed are the needed set),
  `orientation` (the file tasks asked for a neighbourhood: a file of the target's folder in the first three), and `none` (32 scored requests
  in `datasets/no_context.json` that need nothing from the corpus). The shares are 63 : 126 : 32 : 32.
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
- **Run**: `PYTHONPATH=.:evaluation:../evolvable-structure/implementations/python ESOI_OFFLINE=1 python3 -m esoi run context_retrieval --impl hybrid_rrf --keep-going`
  (add `--record` to log it).
- **Limits**: one Python repository and commit-subject wording; the mix is set by value and a sample of real requests should calibrate it; file
  labels stand for relevance, so the right passage inside a needed file is not told from the rest; the cold embedding time is not in the seconds
  per request.
