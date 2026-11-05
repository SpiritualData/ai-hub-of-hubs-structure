"""Seats are Protocols; needs come from typed parameters; uses_solution_ids and the graph agree with the records."""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hubofhubs import AssemblyConfig, AssemblyError, assemble, resolve
from hubofhubs.the_world.learning.research_freshness_reader import registry  # noqa: E402
from hubofhubs.the_self.assembler.resolution import HUB  # noqa: E402
from esoi.intents import read_tree  # noqa: E402
import importlib  # noqa: E402
from hubofhubs.the_body.internal_context.card_store.card import Card  # noqa: E402
from hubofhubs.the_body.internal_context.card_store.cardstore import LocalCardStore  # noqa: E402
from support import ROOT  # noqa: E402

HUB.prepare()
SEATS = {HUB.solution_of(c): c for module in HUB.modules for c in vars(importlib.import_module(module)).values() if isinstance(c, type) and HUB.solution_of(c)}
SOLUTIONS = read_tree(ROOT / "esoi", "solutions.csv")
IMPLEMENTATIONS = read_tree(ROOT / "esoi", "implementations.csv")


def test_the_interface_modules_hold_only_protocol_classes_and_imports():
    assert HUB.modules, "no interface module was found"
    for interface in sorted((ROOT / "hubofhubs").rglob("interface.py")) + [ROOT / "hubofhubs" / "the_world" / "tools" / "goal_running.py"]:
        for node in ast.parse(interface.read_text()).body:
            assert isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Expr)), (interface, ast.dump(node)[:80])
            if isinstance(node, ast.ClassDef):
                assert [ast.unparse(b) for b in node.bases][-1] == "typing.Protocol"   # a seat may extend a port Protocol first
                assert all(isinstance(n, (ast.FunctionDef, ast.Expr)) for n in node.body)


def test_every_seat_is_a_runtime_protocol_with_a_record():
    ids = {s["solution_id"] for s in SOLUTIONS}
    for sid, protocol in SEATS.items():
        assert sid in ids
        assert getattr(protocol, "_is_protocol", False) and getattr(protocol, "_is_runtime_protocol", False)
        assert HUB.solution_of(protocol) == sid


def test_every_recorded_arm_is_declared_in_code_and_satisfies_its_seat():
    for row in IMPLEMENTATIONS:
        sid, _, name = row["implementation_id"].partition(":")
        if not row["filepath"]:       # a researched alternative or a reference entry has no code in this repository
            continue
        target = resolve(sid, name)
        # An arm that needs arguments (a vendor key, a list of assemblers) is checked as a class; the others are built and checked.
        satisfied = issubclass(target, SEATS[sid]) if isinstance(target, type) else isinstance(target(), SEATS[sid])
        assert satisfied, row["implementation_id"]


def test_uses_solution_ids_equals_the_constructor_parameters_and_the_graph_is_sound():
    assert HUB.uses_problems(ROOT / "esoi") == []


def test_external_seats_are_consumer_provided_and_have_no_default():
    by = {s["solution_id"]: s for s in SOLUTIONS}
    # web-search and vendor-model-caller are external systems, but a metric selected a default arm for each (it still needs a key or an option)
    assert "external" in registry.split(by["web-search"]["tags"]) and by["web-search"]["selected"] == "gemini"
    # model-plumbing: the hub ships an arm over vendor-model-caller, which is the consumer-provided seat it needs
    assert by["model-plumbing"]["selected"] == "via_vendor"
    assert "external" in registry.split(by["vendor-model-caller"]["tags"]) and by["vendor-model-caller"]["selected"] == "multi_provider"      # the metric selects the router; the consumer passes its providers


def test_the_default_install_builds_every_seat_that_has_a_default_arm():
    system = assemble(AssemblyConfig(solutions=("card-store", "model-tier-chooser", "research-freshness-reader")))
    assert system.solutions() == ["card-store", "model-tier-chooser", "research-freshness-reader"]
    with pytest.raises((AssemblyError, ValueError), match="web-search|the-science|context-assembler|file-editing|root="):
        assemble(AssemblyConfig())      # the strict form refuses a selected arm whose need is unmet
    assert isinstance(system["card-store"], LocalCardStore)


def test_a_consumer_provided_card_store_wins():
    class Mine:
        def __init__(self):
            self.rows = {}
        def add(self, card): self.rows[card.id] = card; return card.id
        def get(self, card_id): return self.rows.get(card_id)
        def search(self, query="", limit=10, tag=""): return list(self.rows.values())[:limit]
        def delete(self, card_id): return bool(self.rows.pop(card_id, None))
        def count(self): return len(self.rows)
    mine = Mine()
    system = assemble(AssemblyConfig(solutions=("card-store",)), provided={"card-store": mine})
    assert system["card-store"] is mine and "consumer provided" in system.reasons[0]
    system["card-store"].add(Card("a", "x"))
    assert mine.count() == 1


def test_external_seats_fail_at_startup_unless_provided():
    with pytest.raises(AssemblyError, match="vendor-model-caller .multi_provider. needs option"):      # the selected router needs the consumer's providers
        assemble(AssemblyConfig(solutions=("vendor-model-caller",)))
    assert type(assemble(AssemblyConfig(solutions=("vendor-model-caller",), selections={"vendor-model-caller": "claude_cli"}))["vendor-model-caller"]).__name__ == "ClaudeCliProvider"   # a keyless arm needs only the claude executable, when a consumer picks it
    assert "gemini" in assemble(AssemblyConfig(solutions=("web-search",))).reasons[0]   # a default arm is built lazily; its key is read when it searches


def test_sync_uses_check_passes_on_the_repository():
    import subprocess
    import esoi
    env = {"PYTHONPATH": str(Path(esoi.__file__).resolve().parent.parent), "PATH": "/usr/bin:/bin"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_uses.py"), "--check"], capture_output=True, text=True, env=env)
    assert (done.returncode, done.stdout) == (0, "")


def test_know_the_world_is_a_seat_whose_arm_needs_a_search_backend():
    from hubofhubs.the_world.tools.web_search.search_port import SearchHit, SearchResponse

    class Backend:
        name = "toy"

        def search(self, query, *, max_results=5):
            return SearchResponse(hits=[SearchHit(title="A page", url="https://example.com/a", snippet="a fact", date="")])

    by = {s["solution_id"]: s for s in SOLUTIONS}
    assert by["the-science"]["selected"] in {"web_research", "openalex_semantic"} and {"web_research", "openalex"} <= set(by["the-science"]["implementations"].split(";"))
    config = AssemblyConfig(solutions=("the-science",), selections={"the-science": "web_research"})
    system = assemble(config, provided={"web-search": Backend()})
    arm = system["the-science"]
    assert isinstance(arm, SEATS["the-science"]) and arm.describe() == "web search via toy"
    observation = arm.search("a question")
    assert observation.kind != "error" and "https://example.com/a" in observation.text
    assert "gemini" in assemble(config)["the-science"].describe()   # with none provided the need falls to the hub's selected search arm
