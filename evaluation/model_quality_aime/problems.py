"""The AIME 2025 problem text, fetched once from a pinned public mirror and checked against the sha256 recorded in ``cases.json``.

The problems are published by the Mathematical Association of America (AIME 2025 I and II). The mirror's license is MIT (its dataset card),
which does not settle the MAA's rights in the text, so the text is not committed: ``cases.json`` holds ids, gold answers and the
sha256 of each problem, and this loader downloads the two files into ``data/`` (git-ignored) and refuses text that does not match.
"""
import hashlib
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
COMMIT = "a6ad95f611d72cf628a80b58bd0432ef6638f958"      # huggingface.co/datasets/opencompass/AIME2025, 2025-02-25
FILES = {
    "aime2025-I.jsonl": "b91b3c96f05d9635d2a0692b124ebe023c1ff59cb19c074275e6c4b349d0659e",
    "aime2025-II.jsonl": "16a2dcfbbf9db1b11f8a69a3ba5e4cac73e3641b19a37e2307e9c12240bbed5e",
}
URL = "https://huggingface.co/datasets/opencompass/AIME2025/resolve/" + COMMIT + "/{name}"


def fetch(name):
    """The bytes of one pinned file, from ``data/`` or downloaded once; a file whose sha256 differs is refused."""
    path = DATA / name
    if not path.exists():
        DATA.mkdir(exist_ok=True)
        with urllib.request.urlopen(URL.format(name=name), timeout=60) as response:
            path.write_bytes(response.read())
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FILES[name]:
        path.unlink()
        raise RuntimeError(f"{name} does not match the pinned sha256; deleted, fetch again or update the pin")
    return raw


def question_texts():
    """``{source like "aime2025-I.jsonl:3": problem text}`` for all 30 problems."""
    out = {}
    for name in FILES:
        for number, line in enumerate(fetch(name).decode("utf-8").splitlines(), 1):
            out[f"{name}:{number}"] = json.loads(line)["question"]
    return out


def load_cases():
    """The committed cases with the problem text added; each text is checked against the case's ``text_sha256``."""
    texts = question_texts()
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    for case in cases:
        text = texts[case["source"]]
        if hashlib.sha256(text.encode()).hexdigest() != case["text_sha256"]:
            raise RuntimeError(f"{case['id']}: the problem text does not match text_sha256")
        case["question"] = text
    return cases
