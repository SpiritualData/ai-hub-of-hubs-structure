"""BASELINE: a front door that answers but warns on every input, the kind of line a plain install must never show."""


def build(meter):
    return lambda kind, args: {"answer": "ok", "note": "web search could not run here: pip install 'hubofhubs[gemini]'", "steps": [], "stood_in": [], "broken": []}
