"""Scores a context-assembler arm on a harder known-item check: the query describes the paper in other words (a private stage).

Same 3,000-paper sample, same stored vectors, same arms and wiring, same pass rule as ``context_assembler_papers`` (the paper is among
the first 5 ids ranked); only the query differs, and the paper is named by its public identifier. For each of the 300 papers of that stage the query is one short paraphrase of the
abstract's claim, as a person who had not read the paper might type it, written once by the cheapest Gemini text model
(``gemini-2.5-flash-lite``) and kept in the private cache so every arm and every rerun sees the same text. A paraphrase is refused and
rewritten (up to 3 tries) when it shares a run of 4 consecutive words with the paper's title or abstract; the last try is kept if all fail
(the count is in ``README.md``). The paraphrases are committed in ``cases.json`` as the case text (``build_cases.py`` writes them from the
private cache of the generation). The one-time cost of writing them is in the README, not in an arm's row.
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_assembler_papers import score as papers  # noqa: E402
from priced import first_env, price_of, priced  # noqa: E402

MODEL = "gemini-2.5-flash-lite"
PROMPT = """\
Below is the title and abstract of a scientific paper. Write ONE short search request (12 to 25 words) that a person who has not read
the paper might type to find it: say what it is about and what it found or did, in your own plain words. Do not copy the title, and do
not reuse any run of 4 or more consecutive words from the title or abstract. Do not use em dashes. Output only the request.

Title: {title}

Abstract: {abstract}
"""
CACHE_FILE = "paraphrases.json"
TRIES = 3


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def shares_run(candidate, source, n=4):
    spans = {tuple(words(source)[i:i + n]) for i in range(max(0, len(words(source)) - n + 1))}
    mine = words(candidate)
    return any(tuple(mine[i:i + n]) in spans for i in range(max(0, len(mine) - n + 1)))


def paraphrases(positions, sample):
    """{position: text} for the cases, written once and cached in the private folder; returns (texts, tokens in, tokens out, copied)."""
    path = papers.CACHE / CACHE_FILE
    store = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else dict(tokens_in=0, tokens_out=0, copied=0, texts={})
    missing = [p for p in positions if str(p) not in store["texts"]]
    if missing:
        from hubofhubs.models.gemini import GeminiProvider
        provider = priced(GeminiProvider, price_of("gemini", MODEL))(api_key=first_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"))
        for position in missing:
            paper = sample[position]
            source = paper["title"] + " " + paper["abstract"]
            for attempt in range(TRIES):
                text = provider.answer([{"role": "user", "content": PROMPT.format(title=paper["title"], abstract=paper["abstract"])}],
                                       model=MODEL).strip().strip('"').replace("\u2014", ", ")
                if not shares_run(text, source):
                    break
            else:
                store["copied"] += 1
            store["texts"][str(position)] = text
        store["tokens_in"] += provider.tokens_in
        store["tokens_out"] += provider.tokens_out
        path.write_text(json.dumps(store), encoding="utf-8")
    return store


def load_cases():
    return json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))


def adapt(implementation, meter):
    return papers.adapt(implementation, meter, cases=load_cases())


def score_case(fn, case):
    row = papers.score_case(fn, case)
    row["note"] = "" if row["ok"] else f"paraphrase query: not in the top {papers.PASS_AT}"
    return row


def aggregate(rows):
    return papers.aggregate(rows)
