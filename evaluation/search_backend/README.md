# search-backend: does a top-5 hit come from the source that holds the answer?

The seat runs one web search and returns hits. This component asks 40 factual questions and passes an arm when one of its top
five hits comes from a page or site that the dataset names as the question's supporting source.

## Cases

- Dataset: SimpleQA test set (4,326 questions), OpenAI `simple-evals`, license MIT (https://github.com/openai/simple-evals).
- File: https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv, downloaded 2026-10-31,
  sha256 `feee3f7e7db3617e94e8fcf1977b756ec420ef8568f4e0fcbbe0e92e9d5fc032`. Version: the file as of that date (it has no version number).
- Each question's metadata lists the URLs its answer was verified against. Those are the gold URLs.
- Sample: `build_cases.py`, seed 20261031, 40 questions drawn at random from the 4,302 whose gold URLs contain no "/home" (such a
  URL would trip this repository's machine-path check). `cases.json` is that sample and nothing else is committed; to reproduce,
  run `python3 evaluation/search_backend/build_cases.py` and compare the sha256 of `cases.json`.
- The `area` of a case is the dataset's topic; `--sample N` spreads N cases over the topics, and a smaller N is a prefix of a larger.

## Matching rule (written before any run)

A URL is reduced to its host (lower case, leading `www.` removed) and path (trailing slash removed); scheme, query and fragment
are ignored. A hit passes when:

1. its host and path equal those of any gold URL (page match), or
2. its host equals the host of any gold URL (domain match), unless that gold host is a Wikipedia site (`wikipedia.org` or a
   subdomain), where only the page match counts, because a domain match there would accept any article.

An arm that returns an unresolved Google grounding link (host `vertexaisearch.cloud.google.com`) with the source's bare host name as
the hit title is read by that title, for the domain match only. The question passes if any of the first five hits passes.
A search error counts as a failed case, and the note says so.

What this does not see: whether the page really contains the answer (a right site can be the wrong page), and answers found
on sources the dataset does not list.

## Arms and cost

| Arm | Needs | Cost counted |
|---|---|---|
| gemini | a Google key (`GEMINI_API_KEY`, `GOOGLE_API_KEY` or `GOOGLE_AI_API_KEY`) | tokens at the Gemini 2.5 Flash-Lite price ($0.10 in, $0.40 out per million); grounded prompts are free up to 1,500 a day (Google pricing page, read 2026-10-31) and a run stays inside that |
| provider | the same Google key; the hub's Gemini provider, the only hub provider with a native web search (the OpenAI provider has none) | the same |
| searxng | `SEARXNG_URL`, a SearXNG instance of your own | none set here |
| brave, serper, tavily | their API keys | none set here |

An arm whose credential is not set is "not measured: no credential" and writes no result row.

## Run

    PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run search_backend --impl gemini --sample 3
    PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run search_backend --impl gemini --record

The same command with `--impl provider` measures the provider arm. The method is `docs/how-we-measure.md`.
