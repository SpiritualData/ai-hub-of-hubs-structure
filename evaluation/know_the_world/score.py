"""Scores a know-the-world arm: one research question, passed when the gold paper is among the observations returned.

Matching rule (fixed before any run, also written in README.md). A title is lower-cased and reduced to its letters and digits
separated by single spaces. The case passes when the gold paper's reduced title is contained in the reduced text of the
observation the arm returned (its rendered text, plus the title of each hit). The dataset (LitSearch) carries titles and not DOIs,
so the check is by exact title. An observation of kind ``error`` has no text and so fails.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from search_backend.score import PRICES, NoCredential, priced, settings_for  # noqa: E402,F401


def reduced(text):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def observed_text(observation):
    return " ".join([observation.text or ""] + [str(h.get("title", "")) for h in observation.hits])


def adapt(implementation, meter):
    """Build the arm. ``web_research`` runs over the Gemini grounding backend (the seat's search need); the others take what
    their ``ENVIRON`` declares (OpenAlex declares none, so it runs on its keyless allowance with no contact address)."""
    if getattr(implementation, "__name__", "") == "WebResearchAdapter":
        from hubofhubs.websearch.gemini import GeminiGroundingBackend
        arm = implementation(priced(GeminiGroundingBackend(**settings_for(GeminiGroundingBackend)), meter))
    else:
        arm = implementation(**settings_for(implementation))
        meter.wrap(arm, ("search",))
    return lambda kind, args: arm.search(args["question"], max_results=5)


def score_case(fn, case):
    observation = fn("search", {"question": case["question"]})
    if observation.kind == "error":
        raise RuntimeError(observation.error)
    found = reduced(case["gold_title"]) in reduced(observed_text(observation))
    return dict(ok=found, got=(observation.hits[0].get("title", "") if observation.hits else "no hits")[:60],
                note="" if found else f"{len(observation.hits)} hits, gold paper not among them")
