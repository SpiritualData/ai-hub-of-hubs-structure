"""Rebuilds cases.json: 30 HumanEval problems (MIT, https://github.com/openai/human-eval) drawn with a fixed seed.

    python3 build_cases.py HumanEval.jsonl.gz     # the file from the repository's data/ folder

Each problem becomes one file-edit goal: ``solution.py`` holds the prompt (signature and docstring) with a ``pass`` body, and the goal is to
make ``test_solution.py`` pass by implementing the function. The tests are the benchmark's own, unchanged.
"""
import gzip
import json
import random
import sys
from pathlib import Path

SEED = 20261031
COUNT = 30


def main(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        problems = [json.loads(line) for line in fh]
    chosen = sorted(random.Random(SEED).sample(range(len(problems)), COUNT))
    cases = []
    for index in chosen:
        p = problems[index]
        cases.append(dict(id=f"he-{index:03d}", area="humaneval", source=p["task_id"], entry_point=p["entry_point"],
                          stub=p["prompt"].rstrip("\n") + "\n    pass\n", test=p["test"], solution=p["prompt"] + p["canonical_solution"]))
    Path(__file__).with_name("cases.json").write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases written")


if __name__ == "__main__":
    main(sys.argv[1])
