"""Hands reports reach and use for each declared integration of the system asked about."""
from hubofhubs.the_body.hands.integrations import DeclaredAndUsed

DECLARED = [{"name": "a", "system": "s1", "tool": "t"}, {"name": "b", "system": "s1"}, {"name": "c", "system": "s2", "tool": "t"}]


def test_each_declared_integration_says_whether_it_is_reachable_and_used_and_idle_ones_are_marked():
    rows = {r["name"]: r for r in DeclaredAndUsed(DECLARED, [{"used": ["b"]}]).integrations("s1")}
    assert set(rows) == {"a", "b"} and rows["a"]["unused"] and not rows["a"]["used"] and rows["b"]["used"] and not rows["b"]["reachable"] and not rows["b"]["unused"]
