"""Rebuild cases.json for the paraphrase stage: the same 300 papers as the known-item stage, every query a paraphrase. Maintainers only.

    python3 evaluation/context_assembler_paraphrase/build_cases.py

Each paraphrase is written once by ``score.paraphrases`` (the cheapest Gemini text model, refused and rewritten if it copies a run of
4 words from the title or abstract) and committed here as the case text, so the stage is fixed. Titles and abstracts are public.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402
from context_assembler_papers import score as papers  # noqa: E402


def main():
    source = json.loads((Path(papers.__file__).with_name("cases.json")).read_text(encoding="utf-8"))
    sample, ids = papers.pull(), papers.corpus_ids()
    index = {ident: n for n, ident in enumerate(ids)}
    positions = [index[c["gold"]] for c in source]
    store = score.paraphrases(positions, sample)
    cases = [dict(id=f"p-{i + 1:03d}", kind="paraphrase", stratum="paraphrase", gold=c["gold"], query=store["texts"][str(index[c["gold"]])])
             for i, c in enumerate(source)]
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases; {store['copied']} paraphrases still share a 4-word run; generation tokens {store['tokens_in']} in, {store['tokens_out']} out")


if __name__ == "__main__":
    main()
