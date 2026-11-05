"""Scores a Response Writer arm on the results of delegated pieces: a gold answer with its gold links, and pieces that were refused or failed.

An answer case passes when the response contains the answer (any case), every link it names is one of the results' links (checked with the hub's own evidence
check) and at least one gold link is named. A failure case passes when the response names the piece and says it was not done or failed, and says nothing
else a result did not hold. One number: the share of cases passed. No model call."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def adapt(implementation, meter):
    arm = implementation()
    return lambda kind, args: arm.write(args["results"])


def score_case(fn, case):
    from hubofhubs.critique.evidence_check import EvidenceCheck
    text = fn(case["kind"], case["args"])
    want = case["expect"]
    if case["kind"] == "failure":
        ok = want["piece"] in text and bool(re.search(r"not done|failed", text))
        return dict(ok=ok, kind="failure", got=text[:60], note="" if ok else "the response did not say the piece was not done")
    evidence = " ".join(item["url"] for r in case["args"]["results"] for item in r["items"])
    findings = EvidenceCheck().critique(text, evidence)
    named = [u for u in want["links"] if u in text]
    ok = want["answer"].lower() in text.lower() and not findings and bool(named)
    return dict(ok=ok, kind="answer", got=text[:60], note="" if ok else "; ".join(findings) or "the answer or a gold link is missing")


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("answer", "failure")}
