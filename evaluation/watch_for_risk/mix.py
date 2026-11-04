"""The one place that says which kinds of case make up the single score of ``watch_for_risk``.

``MIX`` names the sources (files of ``datasets/``) and every case of each is in the set, so the mix is the sources' sizes: 36 explicit and
24 ambiguous digests. It was fixed by what the author could write, not by a sample of real runs, so it is not a claim about how often real
steps are ambiguous; when a sample of real run digests exists, calibrate the proportion here and nowhere else (take that many cases of a
source with ``[:count]``).
"""
MIX = {"explicit": 36, "ambiguous": 24}
