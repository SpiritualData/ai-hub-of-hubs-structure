"""Seats are Protocols; needs come from typed parameters; uses_solution_ids and the graph agree with the records."""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hubofhubs import HubConfig, HubError, assemble, graph, resolve  # noqa: E402
from hubofhubs import seats  # noqa: E402
from hubofhubs.card import Card  # noqa: E402
from hubofhubs.cardstore import LocalCardStore  # noqa: E402
from support import ROOT  # noqa: E402

SEATS = {"card-store": seats.CardStore, "model-call": seats.ModelCall, "search-backend": seats.SearchBackend,
         "reason-and-answer": seats.TierSelection, "stay-current": seats.FreshnessReading,
         "connect-any-integration": seats.HubScoring, "watch-for-risk": seats.RiskWatching}
SOLUTIONS = graph.read_rows(ROOT / "esoi", "solutions.csv")
IMPLEMENTATIONS = graph.read_rows(ROOT / "esoi", "implementations.csv")


def test_the_seats_module_holds_only_protocol_classes_and_imports():
    tree = ast.parse((ROOT / "hubofhubs" / "seats.py").read_text())
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Expr)), ast.dump(node)[:80]
        if isinstance(node, ast.ClassDef):
            assert [ast.unparse(b) for b in node.bases] == ["typing.Protocol"]
            assert all(isinstance(n, (ast.FunctionDef, ast.Expr)) for n in node.body)


def test_every_seat_is_a_runtime_protocol_with_a_record():
    ids = {s["solution_id"] for s in SOLUTIONS}
    for sid, protocol in SEATS.items():
        assert sid in ids
        assert getattr(protocol, "_is_protocol", False) and getattr(protocol, "_is_runtime_protocol", False)
        from hubofhubs.needs import seat_of
        assert seat_of(protocol) == sid


def test_every_recorded_arm_is_declared_in_code_and_satisfies_its_seat():
    for row in IMPLEMENTATIONS:
        sid, _, name = row["implementation_id"].partition(":")
        target = resolve(sid, name)
        assert isinstance(target(), SEATS[sid]), row["implementation_id"]


def test_uses_solution_ids_equals_the_constructor_parameters_and_the_graph_is_sound():
    needs = graph.declared_needs(IMPLEMENTATIONS)
    assert graph.problems(SOLUTIONS, IMPLEMENTATIONS, needs) == []


def test_external_seats_are_consumer_provided_and_have_no_default():
    by = {s["solution_id"]: s for s in SOLUTIONS}
    for sid in ("model-call", "search-backend"):
        assert {"external", "consumer-provided"} <= set(graph.split(by[sid]["tags"])) and by[sid]["selected"] == ""


def planted(selected="x", tags="", uses="", sid="a", other_sid="b"):
    solutions = [{"solution_id": sid, "selected": selected, "tags": tags}, {"solution_id": other_sid, "selected": "y", "tags": ""}]
    impls = [{"implementation_id": f"{sid}:x", "solution_id": sid, "uses_solution_ids": uses},
             {"implementation_id": f"{other_sid}:y", "solution_id": other_sid, "uses_solution_ids": ""}]
    return solutions, impls


def test_a_planted_mismatch_between_uses_and_parameters_is_reported():
    solutions, impls = planted()
    bad = graph.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()})
    assert any("uses_solution_ids is empty but its constructor parameters need ['b']" in line for line in bad)
    solutions, impls = planted(uses="b")
    assert graph.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()}) == []
    assert any("needs []" not in line and "nothing" in line for line in graph.problems(solutions, impls, {"a:x": set(), "b:y": set()}))


def test_a_planted_cycle_is_reported():
    solutions, impls = planted(uses="b")
    impls[1]["uses_solution_ids"] = "a"
    bad = graph.problems(solutions, impls, {"a:x": {"b"}, "b:y": {"a"}})
    assert any("default arms form a cycle: a -> b -> a" in line for line in bad)


def test_a_need_on_a_seat_with_no_arm_is_reported_unless_consumer_provided():
    solutions, impls = planted(uses="b")
    solutions[1]["selected"] = ""
    assert any("has no default arm and is not tagged consumer-provided" in line
               for line in graph.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()}))
    solutions[1]["tags"] = "external;consumer-provided"
    assert graph.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()}) == []
    solutions[1]["selected"] = "y"
    assert any("tagged consumer-provided but has a default arm" in line for line in graph.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()}))


def test_a_need_on_an_unknown_seat_is_reported():
    solutions, impls = planted(uses="zzz")
    assert any("zzz, which is no solution" in line for line in graph.problems(solutions, impls, {"a:x": {"zzz"}, "b:y": set()}))


def test_the_default_install_builds_every_seat_that_has_a_default_arm():
    system = assemble(HubConfig())
    assert system.seats() == ["card-store", "reason-and-answer"]   # the other two arms have no measured default
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
    system = assemble(HubConfig(seats=("card-store",)), provided={"card-store": mine})
    assert system["card-store"] is mine and "consumer provided" in system.reasons[0]
    system["card-store"].add(Card("a", "x"))
    assert mine.count() == 1


def test_external_seats_fail_at_startup_unless_provided():
    for sid in ("model-call", "search-backend"):
        with pytest.raises(HubError, match=f"{sid}: no arm, not provided"):
            assemble(HubConfig(seats=(sid,)))


def test_sync_uses_check_passes_on_the_repository():
    import subprocess
    import esoi
    env = {"PYTHONPATH": str(Path(esoi.__file__).resolve().parent.parent), "PATH": "/usr/bin:/bin"}
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_uses.py"), "--check"], capture_output=True, text=True, env=env)
    assert (done.returncode, done.stdout) == (0, "")
