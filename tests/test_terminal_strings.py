"""The terminal's default words are generic and a consumer can override them.

The drift check against a consumer app's own English pack belongs to that consumer, not here.
"""
import re

import pytest

from hubofhubs.terminal import strings


@pytest.fixture(autouse=True)
def _clean():
    strings.clear_overrides()
    yield
    strings.clear_overrides()


def test_every_plural_key_has_both_forms_and_placeholders_are_double_braced():
    for key, value in strings.EN.items():
        if key.endswith("_one"):
            assert f"{key[:-4]}_other" in strings.EN, key
        assert not re.search(r"(?<!\{)\{\w+\}(?!\})", value), key
        assert value.strip() and "  " not in value, key


def test_defaults_name_no_consumer_product():
    assert not [k for k, v in strings.EN.items() if re.search(r"(?<![a-z])quest(?![a-z])|qar", v, re.I)]


def test_registered_overrides_win_over_defaults_and_per_call_wins_over_registered():
    assert strings.say("workTrace.group.records") == "From your records"
    strings.register_overrides({"workTrace.group.records": "From your app"})
    assert strings.say("workTrace.group.records") == "From your app"
    assert strings.say("workTrace.group.records", {"workTrace.group.records": "Mine"}) == "Mine"
    assert strings.table()["workTrace.group.records"] == "From your app"
    strings.clear_overrides()
    assert strings.say("workTrace.group.records") == "From your records"


def test_a_consumer_can_add_its_own_record_kind():
    assert not strings.has("workTrace.recordKind.widget")
    strings.register_overrides({"workTrace.recordKind.widget": "Widget"})
    assert strings.has("workTrace.recordKind.widget") and strings.say("workTrace.recordKind.widget") == "Widget"
