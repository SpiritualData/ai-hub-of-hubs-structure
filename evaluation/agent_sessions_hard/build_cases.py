"""Write cases.json for the hard stage of Delegated Agent Sessions: one stub per private case (its id, kind and the digest of its body).

The cases themselves are real deep work and stay outside this public repository: each is a JSON file in a private folder (multi-file coding
changes with hidden tests, milestone deliverables over real records). ``AGENT_SESSIONS_HARD_CASES`` names those folders, separated by
the path separator; each holds a ``cases/`` folder of ``<id>.json`` files. The digest makes a changed private case a changed case set, so a
result recorded on the old body no longer counts.

    AGENT_SESSIONS_HARD_CASES=/private/a:/private/b python3 evaluation/agent_sessions_hard/build_cases.py

Standard library only."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV = "AGENT_SESSIONS_HARD_CASES"


def private_cases():
    """{id: (path, body text)} from every folder ``AGENT_SESSIONS_HARD_CASES`` names."""
    found = {}
    for folder in filter(None, os.environ.get(ENV, "").split(os.pathsep)):
        for path in sorted(Path(folder, "cases").glob("*.json")):
            found[path.stem] = (path, path.read_text(encoding="utf-8"))
    return found


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def main():
    stubs = [{"id": cid, "stratum": json.loads(text)["stratum"], "digest": digest(text)} for cid, (_, text) in sorted(private_cases().items())]
    if not stubs:
        raise SystemExit(f"no private case found: set {ENV}")
    (HERE / "cases.json").write_text(json.dumps(stubs, indent=1) + "\n")
    print(len(stubs), "cases")


if __name__ == "__main__":
    main()
