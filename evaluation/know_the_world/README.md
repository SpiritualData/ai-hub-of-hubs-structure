# know-the-world: is the paper that answers a research question among what the arm returns?

The seat looks up what the world says and returns observations a reader can cite. This component asks 40 literature-search
questions and passes an arm when the gold paper is among the observations it returns.

## Cases

- Dataset: LitSearch (597 literature-search questions about recent ML and NLP papers, each with its gold paper), Princeton NLP;
  code and data license MIT (https://github.com/princeton-nlp/LitSearch; data at https://huggingface.co/datasets/princeton-nlp/LitSearch,
  revision as served on 2026-10-31). The Hugging Face dataset card states no license of its own; the license is the repository's.
- Gold: the paper's title, read from the dataset's `corpus_clean` table by its corpus id. That table carries titles and not DOIs, so
  the check is by exact title (below).
- Sample: `build_cases.py`, seed 20261031, 40 questions drawn at random from the 280 with quality 2 (the dataset's top rating) and
  exactly one gold paper. `cases.json` (sha256 `7be47b7452a1c41b930f2a2386d2dcad16fcabf25cbb32037283857f70d281a4`) is that sample and
  nothing else is committed. The `area` of a case is the dataset's query set; `--sample N` spreads N cases over them.
- The question is given to the arm as written (a full sentence). The two original arms do not rewrite it; the `openalex_keywords*` arms rewrite it themselves, inside the arm, and the `openalex_semantic` arm sends it whole.

## Matching rule (written before any run)

A title is lower-cased and reduced to its letters and digits separated by single spaces. A case passes when the gold paper's reduced
title is contained in the reduced text of the observation the arm returned: its rendered text plus the title of each hit, after
the question itself is removed from that text (an arm echoes the question in its rendering, and some questions name the paper). An
observation of kind `error` fails the case. Each arm is asked for five results.

What this does not see: a paper whose title is printed differently (a subtitle dropped, an abbreviation), and a web arm whose
summary mentions the title without the paper being one of its hits (counted as found). Both are small and are not corrected.

## Arms and cost

| Arm | Runs on | Cost counted |
|---|---|---|
| web_research | the search-backend seat's `gemini` arm (Gemini 2.5 Flash-Lite with Google Search grounding); page fetching is not used | tokens at $0.10 in, $0.40 out per million; grounded prompts are free up to 1,500 a day (Google pricing page, read 2026-10-31) |
| openalex | OpenAlex works search, no key and no contact address | $0 to us: no model is called; OpenAlex bills a search about $0.001 against its small keyless daily allowance (its documentation, read 2026-10-30, per `docs/science-search.md`) |
| openalex_semantic | OpenAlex semantic search (`search.semantic`, GTE Large EN embeddings of titles and abstracts, computed by OpenAlex; we embed nothing), question sent whole | same as `openalex`; the documented limit is 1 request a second, so the arm waits 2 s between calls (1 s drew HTTP 429 on 11 of 40 cases in the first run, whose row is invalid and is superseded by the rerun) (https://help.openalex.org/api/semantic-search.md, read 2026-10-31) |
| openalex_keywords | the same keyword search after a deterministic, model-free rewrite of the question into at most 5 specific terms | $0 model cost, search as `openalex` |
| openalex_keywords_model | the same keyword search after the cheapest Gemini model (`gemini-2.5-flash-lite`, $0.10 in, $0.40 out per million) writes a short keyword query through the `model-call` seat; the deterministic rewrite is the fallback | tokens at those prices plus the search |

OpenAlex's keyless allowance is $0.10 a day shared by every user of the same network address (about 100 searches), so a 40-case run of each
new arm cannot all happen on one day without a key; runs are therefore split across days and the date of each row says which.

## Run

    PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run know_the_world --impl openalex --sample 3
    PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run know_the_world --impl web_research --record

The method is `docs/how-we-measure.md`.
