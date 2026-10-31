"""Scores a know-the-world arm: one research question, passed when the gold paper is among the observations returned.

Matching rule (fixed before any run, also written in README.md). A title is lower-cased and reduced to its letters and digits
separated by single spaces. The case passes when the gold paper's reduced title is contained in the reduced text of the
observation the arm returned (its rendered text, plus the title of each hit), after the question itself is removed from that text: an arm echoes the
question in its rendering and a question can name the paper. The dataset (LitSearch) carries titles and not DOIs,
so the check is by exact title. An observation of kind ``error`` has no text and so fails.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from search_backend.score import PRICES, NoCredential, priced, settings_for  # noqa: E402,F401
from priced import first_env, price_of, priced as priced_provider  # noqa: E402

MODEL = "gemini-2.5-flash-lite"   # the cheapest text model on Google's pricing page (tier_prices.csv); the query-writing arm uses it


def reduced(text):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def observed_text(observation):
    return " ".join([observation.text or ""] + [str(h.get("title", "")) for h in observation.hits])


class GeminiQueryWriter:
    """The ``model-call`` seat for the evaluation: one question to the cheapest Gemini model, counted and priced on the meter."""

    def __init__(self, meter):
        from hubofhubs.models.gemini import GeminiProvider
        self.provider = priced_provider(GeminiProvider, price_of("gemini", MODEL))(api_key=first_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"))
        meter.model = MODEL
        meter.wrap(self.provider, ("answer",))

    def complete(self, prompt, tier=""):
        return self.provider.answer([{"role": "user", "content": prompt}], model=MODEL)


def optional_settings(arm_class):
    """The options the arm's ``ENVIRON`` declares and the process environment supplies, filled the way esoi's consumer environ fills
    them (``environ_fill``); an option with no variable set is left out, so the arm runs keyless. Values are never printed."""
    import os
    from esoi.assemble import environ_fill
    return {option: os.environ[name] for option, name in environ_fill(arm_class, {}, os.environ).items()}


def adapt(implementation, meter):
    """Build the arm. ``web_research`` runs over the Gemini grounding backend (the seat's search need); the others take what
    their ``ENVIRON`` declares (OpenAlex's key is optional: without one it runs on its keyless allowance; no contact address is ever sent)."""
    if getattr(implementation, "__name__", "") == "WebResearchAdapter":
        from hubofhubs.websearch.gemini import GeminiGroundingBackend
        arm = implementation(priced(GeminiGroundingBackend(**settings_for(GeminiGroundingBackend)), meter))
    elif getattr(implementation, "__name__", "") == "SemanticAndWeb":
        from hubofhubs.websearch.gemini import GeminiGroundingBackend
        arm = implementation(priced(GeminiGroundingBackend(**settings_for(GeminiGroundingBackend)), meter), **optional_settings(implementation))
    elif getattr(implementation, "__name__", "") == "OpenAlexKeywordsModel":
        arm = implementation(model=GeminiQueryWriter(meter), **optional_settings(implementation))
    else:
        arm = implementation(**optional_settings(implementation))   # no model is called, so nothing is counted or priced; OpenAlex takes a key when one is set
    return lambda kind, args: arm.search(args["question"], max_results=5)


def score_case(fn, case):
    observation = fn("search", {"question": case["question"]})
    if observation.kind == "error":
        raise RuntimeError(observation.error)
    text = reduced(observed_text(observation)).replace(reduced(case["question"]), " ")   # the arm echoes the question, which can name the paper
    found = reduced(case["gold_title"]) in text
    return dict(ok=found, got=(observation.hits[0].get("title", "") if observation.hits else "no hits")[:60],
                note="" if found else f"{len(observation.hits)} hits, gold paper not among them")
