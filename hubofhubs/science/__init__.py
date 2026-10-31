"""Scholarly search that executes: an OpenAlex arm of the ``know-the-world`` seat (works search with year and open-access
filters, abstracts rebuilt from the inverted index, a DOI lookup) and a small Crossref DOI-lookup helper.

Importing this package runs nothing. ``httpx`` is loaded lazily, only by the default transport (extra ``science``). The
consumer passes the key, the contact address and the limits as arguments; nothing here reads the environment.
Design and sources: ``docs/explanation/science-search.md``.
"""
