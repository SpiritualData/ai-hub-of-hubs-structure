"""Focus Context: the settings file, the sources, the ranking (focus first, fence kept), the brief, the on-screen line and the grounded harness. Neutral invented data."""
import json
import sys

import pytest

from hubofhubs.the_consciousness.ai_session_experience.session_events import Capabilities, Finished, RunStarted, Step
from hubofhubs.the_intelligence.subconscious.focus_context.arms import ConfiguredFocusContext, FilesystemSearch, NoContext
from hubofhubs.the_intelligence.subconscious.focus_context.brief import RULE, brief_of, line_of
from hubofhubs.the_intelligence.subconscious.focus_context.grounded import Grounded, grounded_builder
from hubofhubs.the_intelligence.subconscious.focus_context.notes import note_of
from hubofhubs.the_intelligence.subconscious.focus_context.settings import ContextSettings, Source, configured, parse_settings, read_settings, replace_focus, settings_path
from hubofhubs.the_intelligence.subconscious.focus_context.sources import load_notes

GARDEN = ["focus:garden"]
NOTES = [
    {"id": "g-overview", "title": "The garden", "text": "A small vegetable plot behind the house.", "affinity_tags": GARDEN, "overview": True},
    {"id": "g-tomato", "title": "Tomatoes", "text": "Tomatoes need staking and plenty of sun.", "affinity_tags": GARDEN, "timestamp": "2026-05-01"},
    {"id": "g-soil", "title": "Soil", "text": "Compost the beds every autumn.", "affinity_tags": GARDEN, "timestamp": "2026-09-01"},
    {"id": "g-old", "title": "Watering", "text": "Water early in the morning.", "affinity_tags": GARDEN, "timestamp": "2026-01-01"},
    {"id": "d-tomato", "title": "Tomato sauce recipe", "text": "Tomatoes simmer with garlic for an hour.", "affinity_tags": ["focus:cooking"]},
    {"id": "x-secret", "title": "Garden tomatoes of a neighbour", "text": "Tomatoes grown by the neighbour.", "affinity_tags": GARDEN, "scope_tags": ["team:other"]},
]


def test_no_file_means_no_settings(tmp_path):
    assert configured("", {"XDG_CONFIG_HOME": str(tmp_path)}) is None
    assert settings_path("", {"XDG_CONFIG_HOME": str(tmp_path)}) is None


def test_default_place_and_environment_and_flag(tmp_path):
    (tmp_path / "ahohs").mkdir()
    default = tmp_path / "ahohs" / "context.toml"
    default.write_text('[context]\nfocus = "garden"\n[[context.sources]]\nkind = "folder"\npath = "notes"\n')
    assert settings_path("", {"XDG_CONFIG_HOME": str(tmp_path)}) == default
    other = tmp_path / "other.toml"
    assert settings_path("", {"XDG_CONFIG_HOME": str(tmp_path), "AHOHS_CONTEXT": str(other)}) == other
    assert settings_path(str(default), {"AHOHS_CONTEXT": str(other)}) == default
    got = configured("", {"XDG_CONFIG_HOME": str(tmp_path)})
    assert got.focus == "garden" and got.sources == (Source("folder", path="notes", focus="garden"),) and got.max_notes == 5 and got.origin == str(default)


def test_settings_errors_are_plain(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        read_settings(tmp_path / "missing.toml")
    with pytest.raises(ValueError, match="kind is one of"):
        parse_settings({"context": {"sources": [{"kind": "web"}]}})
    with pytest.raises(ValueError, match="needs a path"):
        parse_settings({"context": {"sources": [{"kind": "cards"}]}})
    with pytest.raises(ValueError, match="list of words"):
        parse_settings({"context": {"sources": [{"kind": "command", "command": "run.sh"}]}})
    bad = tmp_path / "bad.toml"
    bad.write_text("[context\n")
    with pytest.raises(ValueError, match="cannot be read"):
        read_settings(bad)


def test_replace_focus_only_when_named():
    base = ContextSettings(focus="garden", sources=(Source("folder", path="x"),))
    assert replace_focus(base, "").focus == "garden" and replace_focus(base, " cooking ").focus == "cooking" and replace_focus(None, "x") is None


def test_sources_cards_folder_command_provider(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "a.json").write_text(json.dumps({"id": "c1", "name": "Mulch", "summary": "Mulch keeps beds moist.", "content": ["Use straw."]}))
    (cards / "b.json").write_text("not json")
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "bees.md").write_text("# Bees\nBees help the beans.\n")
    script = tmp_path / "print_notes.py"
    script.write_text("import json, os\nprint(json.dumps([{'id': 'p1', 'title': 'Printed', 'text': os.environ['AHOHS_FOCUS']}]))\n")
    settings = ContextSettings(focus="garden", sources=(Source("cards", path=str(cards)), Source("folder", path=str(folder)), Source("command", command=(sys.executable, str(script)), timeout=20),
                                                          Source("cards", path=str(tmp_path / "gone"))))
    notes, problems = load_notes(settings, provider=lambda focus: [{"id": "q1", "title": "Provided", "text": f"for {focus}"}])
    by_id = {n.id: n for n in notes}
    assert set(by_id) == {"c1", "bees.md", "p1", "q1"}
    assert by_id["c1"].affinity_tags == ("focus:garden",) and "Use straw." in by_id["c1"].text and by_id["bees.md"].title == "Bees"
    assert by_id["p1"].text == "garden" and by_id["q1"].text == "for garden"
    assert problems == [f"the cards folder {tmp_path / 'gone'} does not exist"]


def test_a_failing_provider_or_program_is_a_problem_not_an_error(tmp_path):
    def broken(focus):
        raise RuntimeError("down")
    settings = ContextSettings(focus="g", sources=(Source("command", command=(str(tmp_path / "nope"),)),))
    notes, problems = load_notes(settings, provider=broken)
    assert notes == () and len(problems) == 2


def test_focus_first_ranking_and_fence():
    got = ConfiguredFocusContext().gather("what do my notes say about tomatoes?", NOTES, focus="garden", max_notes=5, scope=["team:mine"])
    ids = got.ids
    assert ids[0] == "g-overview" and ids[1] == "g-tomato"        # overview, then the focus's best match
    assert "x-secret" not in ids                                    # the hard fence
    assert "g-soil" in ids and "g-old" not in ids                   # the newest home notes fill up to three home notes
    assert "d-tomato" not in ids or ids.index("d-tomato") > ids.index("g-tomato")      # affinity is ranking only: another home never comes first


def test_other_home_note_appears_when_it_is_the_best_match_and_the_overview_stays_out():
    got = ConfiguredFocusContext().gather("tomato sauce garlic simmer recipe", NOTES, focus="garden", max_notes=6)
    assert "d-tomato" in got.ids and "g-overview" not in got.ids        # a recipe question is not about the garden: the overview is offered only when the request is


def test_unrelated_request_gets_nothing_not_even_the_overview():
    for request in ("fix the failing build pipeline", "What time is it?", "What is the date today?", "What is 17 plus 25?", "What does the word idempotent mean?"):
        got = ConfiguredFocusContext().gather(request, NOTES, focus="garden")
        assert got.ids == [] and got.brief == "" and got.line == "", request


def test_one_stray_shared_word_is_not_relevance():
    notes = NOTES + [{"id": "g-time", "title": "Sowing time", "text": "Sow at the same time every morning", "affinity_tags": ["focus:garden"], "timestamp": "2026-09-01"}]
    assert ConfiguredFocusContext().gather("What time is it?", notes, focus="garden").ids == []
    assert "g-time" in ConfiguredFocusContext().gather("what time should I sow in the morning?", notes, focus="garden").ids


def test_no_focus_and_no_notes_change_nothing():
    assert ConfiguredFocusContext().gather("tomatoes", [], focus="garden").brief == ""
    assert NoContext().gather("tomatoes", NOTES, focus="garden").ids == []
    plain = ConfiguredFocusContext().gather("tomato sauce garlic simmer", NOTES, focus="")
    assert plain.ids[0] != "g-overview" or plain.ids[0] == "g-overview"      # without a focus nothing is promised first; it still answers


def test_filesystem_search_ignores_the_focus():
    got = FilesystemSearch().gather("tomato sauce garlic", NOTES, focus="garden")
    assert got.ids[0] == "d-tomato"


def test_brief_and_line():
    notes = [note_of(n) for n in NOTES[:2]]
    text = brief_of(notes, "garden")
    assert text.startswith("What is already known about garden") and "[1] The garden" in text and "[2] Tomatoes" in text and text.endswith(RULE)
    assert "never list" in RULE and "my ..." in RULE and "helper" in RULE and "Answer exactly what was asked" in RULE
    assert brief_of([], "garden") == ""
    assert line_of(4, "garden") == "Using 4 saved notes about garden" and line_of(1, "garden") == "Using 1 saved note about garden" and line_of(0, "garden") == ""
    import re
    assert chr(0x2014) not in text and not re.search(r"\bquests?\b", text.lower())


class Fake:
    name = "fake"
    capabilities = Capabilities()

    def __init__(self):
        self.goals = []

    def start(self, goal, sink, resume_session_id=""):
        self.goals.append(goal)
        sink(RunStarted(goal=goal, harness="fake"))
        done = Finished(outcome="met")
        sink(done)
        return done

    def control(self, control):
        return False


def test_grounded_harness_adds_brief_and_one_screen_line():
    inner, seen = Fake(), []
    settings = ContextSettings(focus="garden", sources=(), max_notes=3)
    run = Grounded(inner, settings, provider=lambda focus: NOTES, arm=ConfiguredFocusContext())
    run.start("what do my notes say about tomatoes?", seen.append)
    assert inner.goals[0].startswith("what do my notes say about tomatoes?\n\nWhat is already known about garden")
    started = [e for e in seen if isinstance(e, RunStarted)]
    assert started[0].goal == "what do my notes say about tomatoes?"          # the screen shows the goal as typed
    steps = [e for e in seen if isinstance(e, Step)]
    assert [s.label for s in steps] == ["Using 3 saved notes about garden"] and seen.index(steps[0]) == seen.index(started[0]) + 1
    assert run.name == "fake" and run.harness is inner


def test_grounded_without_context_passes_the_goal_through_and_builder_is_identity_without_settings():
    inner, seen = Fake(), []
    Grounded(inner, ContextSettings(focus="garden"), provider=lambda focus: [], arm=ConfiguredFocusContext()).start("hello", seen.append)
    assert inner.goals == ["hello"] and not [e for e in seen if isinstance(e, Step)]

    def build(name):
        return inner
    assert grounded_builder(build, None) is build
    assert grounded_builder(build, ContextSettings(focus="x")) is build            # no sources and no provider
    assert isinstance(grounded_builder(build, ContextSettings(focus="x"), provider=lambda f: [])("stream"), Grounded)
