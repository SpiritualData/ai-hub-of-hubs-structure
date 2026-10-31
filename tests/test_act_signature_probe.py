"""Signature probes: which keywords an installed callable accepts, and the filter that drops the rest."""
import dataclasses

from hubofhubs.act.signature_probe import accepted_fields, accepted_keywords, filter_keywords


def test_signature_probes():
    def fn(a, b=1, *, c=2): ...
    def loose(**kw): ...
    @dataclasses.dataclass
    class Cfg:
        x: int = 0
        y: int = 0
    assert accepted_keywords(fn) == {"a", "b", "c"} and accepted_keywords(loose) is None
    assert accepted_fields(Cfg) == {"x", "y"}
    assert filter_keywords({"a": 1, "z": 2}, {"a"}, "t") == {"a": 1}
    assert filter_keywords({"z": 2}, None, "t") == {"z": 2}
