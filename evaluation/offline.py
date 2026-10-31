"""Shared by the offline components: compare what an arm returned with what the case expects, as plain JSON values."""
import json


def plain(value):
    """``value`` as JSON would carry it (tuples become lists, keys become strings), so a comparison does not depend on the container."""
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def judge(got, case):
    """The score row for one case: it passes when the arm's result equals the case's ``expect``."""
    got, want = plain(got), plain(case["expect"])
    return dict(ok=got == want, got=json.dumps(got)[:60], note="" if got == want else f"expected {json.dumps(want)[:80]}")
