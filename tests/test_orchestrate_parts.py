"""The parts of the Mind and of Critical Thinking that have arms: Context Intake, the Planner, Delegation, the Response Writer, Metric
Translation and Goal Completion, offline, with recording workers."""
from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_intelligence.critical_thinking.goal_completion.goal_completion import EvidenceStandard
from hubofhubs.the_intelligence.mind.delegation.delegation import ToTools
from hubofhubs.the_intelligence.mind.context_intake.intake import OneView
from hubofhubs.the_intelligence.mind.planner.planning import CueRouter, OnePiece
from hubofhubs.the_intelligence.critical_thinking.metric_translation.translation import GoalRecord
from hubofhubs.the_intelligence.mind.response_writer.writer import CitedResults


class Piece:
    def __init__(self, file, text, id="u1"):
        self.file, self.text, self.id = file, text, id


def test_context_intake_merges_and_names_each_source():
    got = OneView().take("q", {"cards": [Card("c1", "a card", "notes")], "pieces": [Piece("net.py", "def retry_delay(): pass")], "offered": [{"id": "o1", "text": "offered"}]},
                         {"answer": "the web says", "items": [{"url": "https://e.org/a", "title": "A"}]})
    assert got["view"].splitlines() == ["[card c1] a card", "[file net.py] def retry_delay(): pass", "[offered] offered", "[world] the web says"]
    assert [s["kind"] for s in got["sources"]] == ["card", "file", "offered", "world"]


def test_the_planner_splits_routes_and_replans_only_what_failed():
    plan = CueRouter().plan("1. Find the latest Rust version.\n2. Implement the function parse_version so that its docstring holds.")
    assert [p["tool"] for p in plan] == ["web-search", "file-editing"] and plan[0]["sub_goal"]["goal"] == "Find the latest Rust version."
    assert CueRouter().plan("Thanks, that worked.")[0]["tool"] == ""
    assert CueRouter().plan("Find papers on eye movement and native language")[0]["tool"] == "the-science"
    again = CueRouter().plan("Look up the latest release; then implement the function f", unmet={"failed_pieces": ["Look up the latest release"]})
    assert [p["piece"] for p in again] == ["Look up the latest release"]
    assert [p["tool"] for p in OnePiece().plan("anything at all?")] == [""]


class Tools:
    def __init__(self):
        self.calls = []

    def use(self, category, request, cancel_check=None, authority=None):
        self.calls.append((category, request, cancel_check))
        return type("Got", (), {"met": True, "output": "done", "error": None, "cost_usd": 0.0})() if category == "file-editing" else \
            type("Resp", (), {"hits": [type("Hit", (), {"title": "T", "url": "https://e.org/x", "snippet": "S"})()], "answer": "found"})()


class Science:
    def search(self, query):
        return type("Obs", (), {"text": "a paper", "kind": "papers"})()


def delegate(pieces, **kwargs):
    tools = Tools()
    return tools, ToTools(tools, Science()).delegate(pieces, **kwargs)


def test_delegation_enforces_authority_budget_and_cancellation():
    pieces = [{"piece": "search", "tool": "web-search"}, {"piece": "edit", "tool": "file-editing"}, {"piece": "think", "tool": ""}]
    tools, results = delegate(pieces)                       # no declared authority: the read-only categories
    assert [r.get("refused") for r in results] == [None, "authority", None] and results[0]["items"][0]["url"] == "https://e.org/x" and len(tools.calls) == 2      # the piece with no worker and an empty view looks on the web (the second call)
    tools, results = delegate(pieces, authority={"allow": ["web-search", "file-editing"]}, budget={"pieces": 1})
    assert [r.get("refused") for r in results] == [None, "budget", "budget"]
    stop = lambda: True
    tools, results = delegate(pieces, authority={"allow": ["web-search"]}, cancelled=stop)
    assert [r.get("refused") for r in results] == ["cancelled"] * 3 and tools.calls == []
    tools, results = delegate([pieces[0]], cancelled=lambda: False)
    assert tools.calls[0][2] is not None                    # the stop hook is handed through Tools
    tools, results = delegate([{"piece": "lit", "tool": "the-science"}])
    assert results[0]["text"] == "a paper" and results[0]["met"] is True


def test_a_failing_worker_is_a_result_not_a_crash():
    class Broken(Tools):
        def use(self, category, request, cancel_check=None, authority=None):
            raise RuntimeError("down")
    results = ToTools(Broken(), Science()).delegate([{"piece": "edit", "tool": "file-editing"}], authority={"allow": ["file-editing"]})
    assert results[0]["error"] == "RuntimeError: down"                      # the answer depends on an edit, so its failure is an error
    results = ToTools(Broken(), Science()).delegate([{"piece": "search", "tool": "web-search"}])
    assert "error" not in results[0] and results[0]["unavailable"] == "web search"      # a search only enriches: it is said, and never fails the answer


def test_the_writer_cites_and_says_what_was_not_done():
    text = CitedResults().write([{"piece": "q", "text": "1.90.0", "items": [{"title": "Rust", "url": "https://blog.rust-lang.org/"}]},
                                 {"piece": "Delete the backups.", "refused": "authority"}, {"piece": "Edit notes.", "error": "down"}])
    assert "1.90.0" in text and "https://blog.rust-lang.org/" in text and "Delete the backups. was not done" in text and "Edit notes. could not be done: down" in text


def test_metric_translation_never_gives_a_child_more_budget_than_its_parent_has():
    assert GoalRecord().translate("do it")["budget"] == {"attempts": 3, "pieces": 8, "usd": None}
    child = GoalRecord().translate("do it", {"id": "p1", "budget": {"attempts": 2, "pieces": 20, "usd": 1.5}})
    assert child["budget"] == {"attempts": 2, "pieces": 8, "usd": 1.5} and child["parent"] == "p1"


def test_goal_completion_reads_coverage_requirements_and_refusals():
    check = EvidenceStandard().check
    assert check("g", "std", {"text": "x", "coverage": {"processed": 1, "total": 9}})["met"] is False
    assert check("g", "the outcome must contain: a; b", "has a and b")["met"] is True
    assert check("g", "the outcome must contain: a; b", "has a")["met"] is False
    assert check("g", "std", {"text": "", "refused": "budget"})["met"] is False


def test_tools_refuses_data_outside_the_data_scope_of_the_authority(tmp_path):
    from hubofhubs.the_world.tools.flow import ToolsComposition
    (tmp_path / "n.txt").write_text("note")

    class Reader:
        def read(self, root, paths=()):
            return {"n.txt": "note"}

    tools = ToolsComposition.__new__(ToolsComposition)
    tools.parts = {"read-files": Reader()}
    mine = {"data_scope": ["ana"]}
    assert tools.use("read-files", {"root": str(tmp_path), "owner": "ana"}, authority=mine) == {"n.txt": "note"}
    import pytest
    with pytest.raises(PermissionError, match="outside the data scope"):
        tools.use("read-files", {"root": str(tmp_path), "owner": "bo"}, authority=mine)
