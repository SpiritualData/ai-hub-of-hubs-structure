# What public research says about each seat

Read 2026-10-31. For each seat: the strongest outside evidence on tasks like the seat's job, what it favours, whether our own
results agree, and what to compare, add, improve or drop. This page guides **which arms to build and compare**. It never selects
an arm and never mixes an outside number into our results (`docs/how-we-measure.md`, `docs/public-evidence.md`).

How to read a grade. Each claim carries the letter that `esoi evidence grade` computes from the registry row
(`hubofhubs/registry/hub_evidence.csv`, rows with ids shown): A to D, from who ran it, whether the method is disclosed, the sample
size, benchmark age and written confounds. One source is never above B, and a vendor or the authors of the method grading
themselves is never above D. Most rows here are flagged `single_source` and `stale` (older than a year), so read every letter as
"worth building an arm to find out", not as a result. Numbers are copied as printed on the page we opened. Everything below that
needs more than a few hundred new embeddings, or a large reranking run, is marked **needs authorization**; reading the existing
production embeddings needs none. No model call was made to write this page.

## context-assembler (find the passage a request needs)

Our task: BEIR NFCorpus, 323 queries, a hit in the top five. Arms: `bm25`, `vector`, `hybrid`, `composite`.

- **Hybrid beats either retriever alone, and how you fuse matters.** On NFCorpus (NDCG@100) lexical alone scored 0.268, semantic
  alone 0.296, reciprocal rank fusion 0.312 and a tuned score combination 0.327 ([Bruch, Gai and Ingber](https://arxiv.org/abs/2210.11934),
  Table 2; `EV-bruch-nfc-cc`, `EV-bruch-nfc-rrf`; grade B each). The paper reports the score combination ahead of reciprocal
  rank fusion on all seven datasets, and finds reciprocal rank fusion sensitive to its parameters. The catch: the combination
  needs a handful of labelled queries to set one weight.
- **A reranker on top is the best-supported next stage.** In [BEIR](https://arxiv.org/abs/2104.08663) (NeurIPS 2021) the BM25 plus
  cross-encoder system had the best average of ten systems (+11 percent over BM25) and 0.350 on NFCorpus against BM25 0.325
  (`EV-beir-ce-nfcorpus`, `EV-beir-ce-avg`; grade B). The cost is a model pass per candidate. For research-paper lookup an LLM
  reranker raised recall@5 from 74.8 to 79.2 ([LitSearch](https://arxiv.org/abs/2407.18940), `EV-litsearch-rerank`).
- **Late interaction did not help here.** The original ColBERT scored 0.305 on NFCorpus, below BM25 (`EV-beir-colbert-nfcorpus`;
  grade B), though it was +2.5 percent on the BEIR average.
- **Hard, reasoning-style queries change the answer.** On [BRIGHT](https://arxiv.org/abs/2407.12883) (ICLR 2025) BM25 scored 14.5
  and the best 7B embedder 22.5; the same 7B embedder family scores 59.0 on MTEB. Rewriting the query with LLM reasoning steps gained
  up to 12.2 points (`EV-bright-bm25`, `EV-bright-rewrite`). Our NFCorpus cases are short topic questions, so this is a different
  circumstance.

**Favoured, with uncertainty:** a hybrid of BM25 and a modern dense model, fused by a weighted score, with a cross-encoder rerank of
the top 20 to 50. Confidence is moderate (two good sources agree on direction; no single source ties all three stages to our
corpus type).

**Do our results agree?** Partly. `vector` (nDCG@10 0.3365) beat `bm25` (0.3065) by a small margin on the same 323 queries, and
passes were 205 against 200 of 323, which is not shown to be a real difference. BEIR in 2021 had dense models losing to BM25 on
NFCorpus (TAS-B 0.319 against 0.325); a 2026 small embedder (`bge-small-en-v1.5`, 34.3 on the model card) wins by a few points.
The likely reason for the flip is the embedding model's age. `hybrid` and `composite` are not yet measured (embedding was not
authorized), so the main public prediction, that fusion beats both parts, is untested by us.

- **Keep comparing:** `bm25`, `vector`, `hybrid` (run once the index is authorized).
- **Add:** a weighted score-fusion arm (no new library, about 40 lines, tune one weight on a split of the cases); a cross-encoder
  rerank stage over `hybrid` (a small ONNX or sentence-transformers model, extra per arm, about 60 lines; 323 queries times 20
  candidates is about 6,500 pairs, **needs authorization**).
- **Improve:** the hybrid's hand-set vector weight (currently set from a different task) can be tuned on a split of these cases; a
  better default embedder (`Qwen3-Embedding-0.6B` or `EmbeddingGemma-300m`, maker-reported MTEB scores only, grade D, and not
  comparable with the `bge-small` figure; re-embedding is **needs authorization**).
- **Drop as not worth measuring:** `composite` (concatenating two ranked lists) has no public support next to rank or score fusion;
  keep it only if production behaves that way. Late interaction (`PyLate`) is low priority on this corpus type.

## call-a-model (vendor models; router failover)

- **Public evidence is thin.** We found no peer-reviewed or independent study of provider failover; it is engineering practice,
  not a research question. For choosing between vendor models, independent aggregate indexes exist (see `docs/public-benchmarks.md`)
  and serve as a shortlist only.
- **Our results.** Failover is deterministic mechanics: `multi_provider` 30 of 30, `single_provider` 12 of 30 on simulated
  outages. The three vendor arms on 50 cases passed 50, 46 and 47, a spread that 50 cases cannot separate.
- **Recommendation.** Keep all current arms. Add nothing from public research. Drop nothing.

## search-backend (web search hits containing the source)

- **The independent comparison we found is close.** On 100 real queries, five results each, the [AIMultiple agent search
  benchmark](https://aimultiple.com/agentic-search) scored Brave 14.89, Exa 14.39, Parallel Search Pro 14.21, Tavily 13.67,
  Perplexity 12.96 (rows `EV-am-score-*`, already in the registry; grade C, sponsored environment, intervals overlap). Vendor
  BrowseComp tables (`EV-par-browsecomp-*`) are vendor-run, grade D.
- **Favoured:** no search API is shown best. Brave, Exa and Parallel form a leading group; difference between them is within noise.
- **Our results.** `gemini` (grounded search) passed 28 to 30 of 40; `provider` passed 12 to 14 of 40 on SimpleQA source URLs. No
  public source compares those two, so there is neither agreement nor contradiction.
- **Add:** a Brave Search API arm and an Exa arm, each a thin HTTP adapter (about 80 lines, a key each, 40 cases times one call:
  trivial cost). **Keep:** `gemini`, `provider`. **Drop:** nothing.

## know-the-world (find papers for a research question)

Our task: 40 LitSearch questions, the gold paper among the observations. Arms: `web_research` (6 to 8 of 40), `openalex` (2 of 40).

- **Dense retrieval over a paper index wins by a wide margin.** On LitSearch ([EMNLP 2024](https://arxiv.org/abs/2407.18940)) BM25
  reached recall@5 of 50.0 on specific questions and a 7B embedding model 74.8; Google Search, Google Scholar and Elicit scored 23.1,
  20.5 and 23.1 on the inline-citation questions, against 67.7 for the embedder (`EV-litsearch-*`; grade B to C).
- **Agents are promising but self-reported.** [PaSa](https://arxiv.org/abs/2501.10120) reports large recall gains over Google with
  GPT-4o on its own benchmark (`EV-pasa-recall`; grade D, the authors' own system).
- **OpenAlex as a source is sound.** Its reference counts were on par with Web of Science and Scopus, with fewer abstracts
  ([Culbert et al.](https://arxiv.org/abs/2401.16359), `EV-culbert-openalex`). That says the data are good, not that keyword
  search over them answers a full-sentence question.
- **Documented, not measured:** OpenAlex's own docs describe a `search.semantic` mode that uses embeddings and a `rerank` option
  at an extra cost (maintainer documentation, read 2026-10-31; no number to grade).

**Favoured, with uncertainty:** semantic (embedding) search over titles and abstracts, optionally LLM reranked. Our `openalex` arm
issues a keyword query with the whole sentence, which is the weakest family in the paper, and it also searches a far larger corpus
than the benchmark's 64,183 papers, which the paper itself notes depresses search-engine scores. So 2 of 40 and 6 to 8 of 40 agree
in direction with public results and are not a contradiction.

- **Keep:** `web_research`, `openalex` keyword as the baseline.
- **Add:** an `openalex` arm using `search.semantic` (no new library, about 30 lines, about $1 per 1,000 calls so 40 cases is
  trivial); an arm that has a cheap model rewrite the question into keywords before the keyword search (about 40 lines);
  Semantic Scholar's search and the Asta Paper Finder as comparators (both already candidates).
- **Improve:** extract the title from each observation for matching so the check is not hurt by long snippets (a case-set matter).
- **Watch, do not build:** a PaSa-style agent (authors' claim only). Embedding a whole paper corpus ourselves is
  **needs authorization**.
- **Drop:** nothing.

## act-in-the-world (coding and file-edit goals)

Our task: 30 HumanEval-size goals. Arms: `fast_edit` (30 of 30, $0.005, 77 s), `subprocess_goal_runner` (30 of 30, $0.147, 641 s),
`stream_json_goal_runner`, `acp_deep_runner` (not measurable here).

- **A thin pipeline can match an agent loop on well-specified work.** [Agentless](https://arxiv.org/abs/2407.01489), a fixed
  locate, repair and validate pipeline, reported 32.00 percent on SWE-bench Lite at $0.70 per issue (authors' own, grade D).
- **Edit format moves results, per model.** Aider's maintainer measured 61 percent with unified diffs against 20 percent with
  search and replace on one 2023 model ([Aider](https://aider.chat/docs/unified-diffs.html), `EV-aider-udiff`; grade D). Test the
  format per model.
- **Harness versus model.** On the Vals board with Claude Opus 4.8, the minimal `mini-swe-agent` scored 88.6 and Claude Code 85.8
  on SWE-bench Verified (`EV-vals-swe-*`, in the registry), but that board is saturated and the harness is entangled with the
  model. [Terminal-Bench 2.0](https://arxiv.org/abs/2601.11868) still separates agents: frontier results were below 65 percent
  (`EV-tbench-ceiling`; grade B).
- **Favoured:** for small, well-specified edits the cheapest arm that passes (`fast_edit`); for long tasks no harness has strong
  independent evidence, and the public boards are model-and-harness mixes.
- **Do our results agree?** Yes on cost and time. They cannot rank quality, because both groups pass 30 of 30: the case set is at
  its ceiling, a circumstance and not a result.
- **Add:** `mini-swe-agent` as a thin-harness arm (a pip package, about 100 lines); an edit-format variant of `fast_edit`
  (whole file, search and replace, unified diff) per model. **Improve:** a harder case set (a SWE-bench Pro or Terminal-Bench style
  subset), which is paid model work and **needs authorization**. **Keep:** all current arms. **Drop:** nothing.

## watch-for-risk (overseer versus none)

Our task: 36 steps, 18 irreversible and 18 ordinary. `overseer` 35 of 36 (33 of 36 with the other cheap model), `none` 18 of 36.

- **A separate model reading the run catches much, not everything.** In [SHADE-Arena](https://arxiv.org/abs/2506.15740) the best
  monitor reached AUC 0.87 (`EV-shade-monitor`; grade C). An OpenAI study found a monitor reading the reasoning far better than one
  reading actions alone, and a weaker model could monitor a stronger one (`EV-cot-monitor`, vendor, no figures).
- **Ambiguity is where it fails.** An independent stress test of Claude Code's auto mode classifier measured an 81.0 percent false
  negative rate (95 percent interval 73.8 to 87.4, 253 actions) on deliberately ambiguous authorization cases, with a 31.9 percent
  false positive rate on the actions it evaluated ([arXiv 2604.04978](https://arxiv.org/abs/2604.04978), `EV-autostress-fnr`,
  `EV-autostress-fpr`; grade B). Anthropic's own figures were 17 percent false negatives on 52 real overeager actions and 0.4
  percent false positives on 10,000 real calls, with a two-stage design (a fast filter then a closer check)
  ([post](https://www.anthropic.com/engineering/claude-code-auto-mode), vendor, grade D). The two disagree because the workloads
  differ.
- **A design-level defence trades a little utility for a guarantee.** [CaMeL](https://arxiv.org/abs/2503.18813) solved 77 percent
  of AgentDojo tasks with provable security against 84 percent undefended (authors' claim, grade D).

**Favoured, with uncertainty:** an added model monitor in two stages, plus a deterministic gate for actions that must never run
unconfirmed, because no monitor is reliable on ambiguous cases.

**Do our results agree?** On direction, yes: the overseer beats nothing. But our cases state the step plainly, and `none` scores 18 of
36 only because it lets everything through, so 35 of 36 is likely an upper bound. The independent study predicts a much lower figure on ambiguous steps.

- **Keep:** `overseer`, `none` (as the floor). **Add:** a two-stage overseer (cheap filter then a closer check, about 60 lines);
  a rule-based consent gate arm with no model (Cedar or OPA style, about 50 lines); and a set of ambiguous cases, which costs
  nothing to write. **Watch:** open monitor models (gpt-oss-safeguard, LlamaFirewall AlignmentCheck), which mean local model
  runs and **need authorization** if large. **Drop:** nothing.

## card-store

No public task resembles a card store's job (correctness of store, merge and tidy). Retrieval quality over cards falls under
context-assembler above. Our `local_card_store` passes 35 of 35. **Recommendation:** no change from public research; do not
chase vector store leaderboards without a cardinality that needs one.

## reason-and-answer (tier selection)

- **Routing and cascades cut cost, per their authors.** [RouteLLM](https://arxiv.org/abs/2406.18665) reports cost down by over 2
  times in certain cases without hurting quality; [FrugalGPT](https://arxiv.org/abs/2305.05176) reports matching GPT-4 at up to
  98 percent lower cost (`EV-routellm-cost`, `EV-frugalgpt-cost`; both grade D: the authors' own methods on older models).
- **Favoured, weakly:** try the cheapest sufficient tier and escalate on a failed check. Our `tier_selector` (36 of 36) is a
  rule-based selector on authored cases, so it is a mechanics test and cannot agree or disagree.
- **Add:** a cascade arm that escalates when a checker rejects the answer (about 80 lines, reuses the think-critically checker;
  small paid calls). **Consider later:** a learned router like RouteLLM once logged outcomes exist (needs training data). **Keep:**
  `tier_selector`. **Drop:** nothing.

## Mind seats with no arm yet

- **think-critically.** [MiniCheck](https://arxiv.org/abs/2404.10774) (EMNLP 2024) reports a 770M-parameter checker at GPT-4
  accuracy with about 400 times lower cost on LLM-AggreFact (`EV-minicheck-cost`; grade D, the authors' own model). **Add** a
  MiniCheck arm (or Vectara HHEM-2.1-Open, an existing candidate), a CPU-capable extra, about 60 lines, scored on a small
  LLM-AggreFact subset. The model download is large, not an embedding run.
- **hold-the-intents.** No public task represents a hierarchy of life intents (`docs/public-benchmarks.md`). No recommendation;
  an honest gap.
- **keep-it-generic.** The check is a scan of our own files; no outside evidence applies.
- **take-in-the-world.** Evidence gathered so far is vendor-run (search-engine BrowseComp tables); nothing graded above D, so no arm
  recommendation from public research this round.

## Limits of this page

All papers were read from their abstract pages, and the tables of BEIR, LitSearch, BRIGHT and the fusion paper from their PDFs. Two
points rest on secondary reading: the PaSa gain is quoted from the abstract (absolute or relative is not stated there), and the
Terminal-Bench figure is an upper bound from the abstract. Recheck any row before leaning on it.
