"""Scores a search-backend arm: one factual question, the top five hits, passed when a hit comes from the gold source.

Matching rule (fixed before any run, also written in README.md). A URL is reduced to its host (lower case, a leading ``www.``
removed) and its path (a trailing slash removed); scheme, query and fragment are ignored. A hit passes when its host and path equal
those of any gold URL of the question (page match), or when its host equals the host of any gold URL (domain match), except that
a gold host that is a Wikipedia site (``wikipedia.org`` or a subdomain) needs the page match, because a domain match there would
accept any article. An arm that returns an unresolved Google grounding link (host vertexaisearch.cloud.google.com) with the
source's bare host name as the hit title is read by that title for the domain match only.

An arm needs a credential or a service address, read here by the names the arm itself declares (``REQUIRES``); with none set the
arm is "not measured: no credential" and ``adapt`` raises, so no row is written.
"""
import os
from urllib.parse import urlsplit

TOP = 5
# USD per million tokens for the model the Gemini grounding arm uses (Google AI pricing page, read 2026-10-31).
# Grounded prompts are free up to 1,500 a day, shared across Flash models; a run stays inside that, so no search fee is added.
PRICES = {"gemini-2.5-flash-lite": (0.10, 0.40)}


class NoCredential(RuntimeError):
    """The arm cannot run here: no key or address is set."""


def key_of(url):
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().split("@")[-1].split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    return host, parts.path.rstrip("/")


def is_wikipedia(host):
    return host == "wikipedia.org" or host.endswith(".wikipedia.org")


REDIRECT_HOSTS = ("vertexaisearch.cloud.google.com",)


def from_gold_source(url, gold_urls, title=""):
    host, path = key_of(url)
    if host in REDIRECT_HOSTS and title and "." in title and " " not in title.strip():
        host, path = key_of("//" + title.strip())   # an unresolved Google grounding link: its title is the source's host name
        path = None                                 # the page is unknown, so only a domain match is possible
    if not host:
        return False
    for gold in gold_urls:
        gold_host, gold_path = key_of(gold)
        if host == gold_host and (path == gold_path and path is not None or not is_wikipedia(gold_host)):
            return True
    return False


def settings_for(arm_class):
    """The constructor keywords the arm's declared environment variables name, read from the environment; NoCredential when one is unset."""
    from esoi.assemble import environ_declared
    found = {}
    for option, names in environ_declared(arm_class).items():
        names = (names,) if isinstance(names, str) else names
        value = next((os.environ[n] for n in names if os.environ.get(n)), "")
        if not value:
            raise NoCredential(f"not measured: no credential ({' or '.join(names)} is not set)")
        found[option] = value
    return found


def priced(backend, meter):
    """Count the backend's searches on the meter and add the token cost of each (the arm keeps ``tokens_in``/``tokens_out``)."""
    price = PRICES.get(getattr(backend, "model", ""), (0.0, 0.0))
    meter.model = getattr(backend, "model", None) or meter.model
    inner = backend.search

    def counted(query, **kwargs):
        meter.record()
        before = (getattr(backend, "tokens_in", 0), getattr(backend, "tokens_out", 0))
        try:
            return inner(query, **kwargs)
        finally:
            used_in = getattr(backend, "tokens_in", 0) - before[0]
            used_out = getattr(backend, "tokens_out", 0) - before[1]
            meter.tokens_in += used_in
            meter.tokens_out += used_out
            meter.cost_usd += (used_in * price[0] + used_out * price[1]) / 1_000_000
    backend.search = counted
    return backend


def adapt(implementation, meter):
    backend = priced(implementation(**settings_for(implementation)), meter)
    return lambda kind, args: [(h.url, h.title) for h in backend.search(args["question"], max_results=TOP).hits[:TOP]]


def score_case(fn, case):
    hits = fn("search", {"question": case["question"]})
    hit = next((u for u, t in hits if from_gold_source(u, case["gold_urls"], t)), None)
    return dict(ok=hit is not None, got=(hit or (hits[0][0] if hits else "no hits"))[:60],
                note="" if hit else f"{len(hits)} hits, none from the gold source")
