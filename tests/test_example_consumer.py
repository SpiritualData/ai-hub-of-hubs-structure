"""A second consumer works with no content from the first, and the hub holds none of the second's names."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import example_consumer  # noqa: E402
from support import ROOT  # noqa: E402

FIRST_CONSUMER_TERMS = re.compile(r"quest|qar|spiritual|payal|joshua", re.I)
SECOND_CONSUMER_TERMS = re.compile(r"acme", re.I)


def test_the_second_consumer_assembles_its_system_from_its_own_part():
    system = example_consumer.build_system()
    arm = system[example_consumer.SEAT]
    picked = arm.select({"fast": [{"provider": "p", "model": "m1"}, {"provider": "p", "model": "m2"}]}, [])
    assert picked["fast"]["arm"] == ("p", "m1")
    assert system.reasons == (system.reasons[0],) and "acme-flat (layer: consumer selections" in system.reasons[0]


def test_the_hub_default_still_works_for_a_consumer_that_selects_nothing():
    system = example_consumer.build_system(use_own=False)
    assert "tier_selector (layer: hub default" in system.reasons[0]


def test_the_example_consumer_has_no_content_of_the_first_consumer():
    assert not FIRST_CONSUMER_TERMS.findall((ROOT / "tests" / "example_consumer.py").read_text())


def test_the_hub_code_holds_no_name_of_the_second_consumer_and_no_content_of_the_first():
    leaks = []
    for path in (ROOT / "hubofhubs").rglob("*.py"):
        text = path.read_text()
        if SECOND_CONSUMER_TERMS.search(text):
            leaks.append(f"{path.name}: second consumer")
        if re.search(r"\bquest[_ ]ai[_ ]runner\b|\bqar\b", text, re.I):
            leaks.append(f"{path.name}: first consumer")
    assert not leaks, leaks
