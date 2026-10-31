"""Write evaluation/call_a_model/cases.json: a fixed-seed sample of the GSM8K test split.

    python3 scripts/sample_gsm8k.py PATH_TO_test.jsonl [--n 50] [--seed 20261031]

The split is the official one from github.com/openai/grade-school-math (MIT), one JSON object per line with ``question`` and ``answer``;
the gold final answer is the text after ``####``. Cases are drawn with ``random.Random(seed).sample`` over line numbers, so the same
file, seed and n give the same cases. Prints the sha256 of the input so the README can pin the exact file.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "evaluation" / "call_a_model" / "cases.json"


def gold(answer):
    return answer.rsplit("####", 1)[1].strip().replace(",", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20261031)
    args = parser.parse_args()
    raw = Path(args.source).read_bytes()
    lines = raw.decode("utf-8").splitlines()
    picked = sorted(random.Random(args.seed).sample(range(len(lines)), args.n))
    cases = []
    for index in picked:
        row = json.loads(lines[index])
        cases.append({"id": f"gsm8k-test-{index:04d}", "area": "grade-school-math", "kind": "solve", "question": row["question"], "expect": gold(row["answer"])})
    OUT.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases of {len(lines)} written to {OUT}; source sha256 {hashlib.sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
