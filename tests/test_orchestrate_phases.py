"""The phase chain stops at the first terminal result and passes one shared state."""
from types import SimpleNamespace

from hubofhubs.orchestrate.phases import run_phases


def test_phases_run_in_order_on_one_state_until_a_result():
    state, seen = SimpleNamespace(trail=[]), []

    def phase(name, result=None):
        def run(rs):
            assert rs is state
            rs.trail.append(name)
            seen.append(name)
            return result
        return run

    assert run_phases(state, [phase("a"), phase("b", "done"), phase("c")]) == "done"
    assert seen == ["a", "b"] and state.trail == ["a", "b"]


def test_every_phase_returning_none_gives_none_and_an_empty_chain_too():
    assert run_phases(object(), [lambda rs: None, lambda rs: None]) is None
    assert run_phases(object(), []) is None
