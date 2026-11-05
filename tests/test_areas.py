"""The composition arms of the areas, run for real over fakes: each uses the seats it is handed and returns what a caller of the area
wants. No model call, no network."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs  # noqa: E402
from hubofhubs.act.folder_writer import FolderWriter  # noqa: E402
from hubofhubs.act.tier_registry import TierRegistry  # noqa: E402
from hubofhubs.areas import PromptsAsData, RegistryResearch, WorldComposition, config_share  # noqa: E402
from hubofhubs.critique.evidence_check import EvidenceCheck  # noqa: E402
from hubofhubs.tiers import TierSelector  # noqa: E402


class Hit:
    def __init__(self, title, url):
        self.title, self.url, self.snippet = title, url, ""


class Response:
    def __init__(self, hits, answer=""):
        self.hits, self.answer = hits, answer


class FakeSearch:
    def search(self, query, *, max_results=5, instruction=None):
        return Response([Hit("Rust", "https://blog.rust-lang.org/")], answer="1.90.0")


class FakePapers:
    def search(self, queries, *, max_results=None, fresh=False):
        return Response([Hit("A paper on Rust", "https://doi.org/10.1/x")])


class RecordingModel:
    def __init__(self):
        self.asked = []

    def complete(self, prompt, tier=""):
        self.asked.append((prompt, tier))
        return "ok"


def test_take_in_the_world_returns_the_answer_with_its_sources_and_adds_papers_when_asked():
    class FakeTools:
        def use(self, category, request):
            assert category == "web-search"
            return FakeSearch().search(request)
    arm = WorldComposition(FakeTools(), FakePapers(), None, None)
    plain = arm.take_in("Rust")
    assert plain["answer"] == "1.90.0" and [i["url"] for i in plain["items"]] == ["https://blog.rust-lang.org/"]
    scholarly = arm.take_in("Rust", scholarly=True)
    assert [i["title"] for i in scholarly["items"]] == ["Rust", "A paper on Rust"]


def test_model_plumbing_asks_the_model_the_tier_chooser_measured_best():
    from hubofhubs.models.via_provider import ViaVendor

    class Vendor:
        def __init__(self):
            self.asked = []

        def answer(self, messages, *, model, system=None, layers=None):
            self.asked.append((messages[-1]["content"], model))
            return "ok"

    vendor = Vendor()
    arm = ViaVendor(vendor, TierSelector())
    assert arm.ask("hello", "cheap") == "ok"
    chosen = TierSelector().choose()["cheap"]["arm"][1]
    assert vendor.asked == [("hello", chosen)]
    arm.ask("hello", "my-own-model")                         # a name the chooser does not list is passed on as the model
    assert vendor.asked[-1] == ("hello", "my-own-model")


def test_stay_current_lists_the_areas_older_than_ninety_days():
    arm = RegistryResearch(hubofhubs.registry.RegistryScan())
    assert arm.stale_areas("2026-10-31") == []
    assert len(arm.stale_areas("2027-06-01")) == len(hubofhubs.registry.read("hubs.csv"))


def test_the_connection_metric_reports_the_share_that_needs_no_code():
    assert 0.0 <= config_share() <= 1.0 and config_share("no-such-area") == 0.0


def test_keep_it_generic_finds_a_vendor_branch_in_the_hub_and_reports_the_rest():
    stay = RegistryResearch(hubofhubs.registry.RegistryScan())
    arm = PromptsAsData(stay)
    report = arm.audit(["gemini"])
    assert set(report) == {"vendor_branches", "stale_areas", "config_share"}
    assert arm.audit([])["vendor_branches"] == []


def test_the_evidence_check_flags_only_links_the_evidence_does_not_hold():
    check = EvidenceCheck()
    assert check.critique("See https://example.org/a and https://other.org/b.", "x https://www.example.org/a/ y") == ["link not in the evidence: https://other.org/b"]
    assert check.critique("no links here", "") == []


def test_the_folder_writer_stays_inside_its_folder_and_backs_up_what_it_replaces(tmp_path):
    writer = FolderWriter(str(tmp_path))
    assert writer.write_file("notes.md", "one").ok and writer.write_file("notes.md", "two").ok
    assert writer.read_file("notes.md") == "two" and len(list((tmp_path / ".hubofhubs-backups").iterdir())) == 1
    assert not writer.write_file("../outside.md", "x").ok and not writer.write_file(".env", "x").ok
    assert writer.read_file("../outside.md") is None


def test_the_tier_registry_maps_a_runner_tier_to_the_chosen_model():
    registry = TierRegistry(TierSelector())
    assert registry.resolve_tier("balanced") == TierSelector().choose()["mid"]["arm"][1]
    with pytest.raises(KeyError):
        registry.resolve_tier("no-such-tier")
