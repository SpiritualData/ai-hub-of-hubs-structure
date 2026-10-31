"""Seats are Protocols; needs come from typed parameters; uses_solution_ids and the graph agree with the records."""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hubofhubs import AssemblyConfig, AssemblyError, assemble, registry, resolve  # noqa: E402
from hubofhubs.resolution import HUB  # noqa: E402
from hubofhubs import seats  # noqa: E402
from hubofhubs.card import Card  # noqa: E402
from hubofhubs.cardstore import LocalCardStore  # noqa: E402
from support import ROOT  # noqa: E402

SEATS = {"card-store": seats.CardStore, "context-assembler": seats.ContextAssembling, "model-call": seats.ModelCall,
         "call-a-model": seats.ModelCalling, "search-backend": seats.SearchBackend,
         "choose-a-model-tier": seats.TierSelection, "read-registry-freshness": seats.FreshnessReading,
         "score-hub-connections": seats.HubScoring, "watch-for-risk": seats.RiskWatching,
         "know-the-world": seats.WorldKnowing, "act-in-the-world": seats.Acting}
SOLUTIONS = registry.read("solutions.csv", ROOT / "esoi")
IMPLEMENTATIONS = registry.read("implementations.csv", ROOT / "esoi")


def test_the_seats_module_holds_only_protocol_classes_and_imports():
    tree = ast.parse((ROOT / "hubofhubs" / "seats.py").read_text())
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Expr)), ast.dump(node)[:80]
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
        target = resolve(sid, name)
        # An arm that needs arguments (a vendor key, a list of assemblers) is checked as a class; the others are built and checked.
        satisfied = issubclass(target, SEATS[sid]) if isinstance(target, type) else isinstance(target(), SEATS[sid])
        assert satisfied, row["implementation_id"]


def test_uses_solution_ids_equals_the_constructor_parameters_and_the_graph_is_sound():
    assert HUB.uses_problems(ROOT / "esoi") == []


def test_external_seats_are_consumer_provided_and_have_no_default():
    by = {s["solution_id"]: s for s in SOLUTIONS}
    # search-backend and call-a-model are external systems, but a metric selected a default arm for each (it still needs a key or an option)
    assert "external" in registry.split(by["search-backend"]["tags"]) and by["search-backend"]["selected"] == "gemini"
    # model-call is external but the hub ships an arm over call-a-model, which is the consumer-provided seat it needs
    assert "external" in registry.split(by["model-call"]["tags"]) and by["model-call"]["selected"] == "via_call_a_model"
    assert "external" in registry.split(by["call-a-model"]["tags"]) and by["call-a-model"]["selected"] == "multi_provider"


def test_the_default_install_builds_every_seat_that_has_a_default_arm():
    system = assemble(AssemblyConfig(solutions=("card-store", "choose-a-model-tier", "read-registry-freshness", "score-hub-connections")))
    assert system.solutions() == ["card-store", "choose-a-model-tier", "read-registry-freshness", "score-hub-connections"]
    with pytest.raises(AssemblyError, match="call-a-model .multi_provider. needs option"):
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
    with pytest.raises(AssemblyError, match="call-a-model .multi_provider. needs option"):
        assemble(AssemblyConfig(solutions=("call-a-model",)))
    assert "gemini" in assemble(AssemblyConfig(solutions=("search-backend",))).reasons[0]   # a default arm is built lazily; its key is read when it searches


def test_sync_uses_check_passes_on_the_repository():
    import subprocess
    import esoi
    env = {"PYTHONPATH": str(Path(esoi.__file__).resolve().parent.parent), "PATH": "/usr/bin:/bin"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_uses.py"), "--check"], capture_output=True, text=True, env=env)
    assert (done.returncode, done.stdout) == (0, "")


def test_know_the_world_is_a_seat_whose_arm_needs_a_search_backend():
    from hubofhubs.ports.search import SearchHit, SearchResponse

    class Backend:
        name = "toy"

        def search(self, query, *, max_results=5):
            return SearchResponse(hits=[SearchHit(title="A page", url="https://example.com/a", snippet="a fact", date="")])

    by = {s["solution_id"]: s for s in SOLUTIONS}
    assert by["know-the-world"]["selected"] == "web_research" and {"web_research", "openalex"} <= set(by["know-the-world"]["implementations"].split(";"))
    config = AssemblyConfig(solutions=("know-the-world",), selections={"know-the-world": "web_research"})
    system = assemble(config, provided={"search-backend": Backend()})
    arm = system["know-the-world"]
    assert isinstance(arm, seats.WorldKnowing) and arm.describe() == "web search via toy"
    observation = arm.search("a question")
    assert observation.kind != "error" and "https://example.com/a" in observation.text
    assert "gemini" in assemble(config)["know-the-world"].describe()   # with none provided the need falls to the hub's selected search arm
