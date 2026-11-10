"""Rebuild cases.json for Structure In View: is the tree of solutions right, collapsed by default, complete when opened, and safe for an unknown solution?

Events and records are invented (``fixture.py``) and every expected value is written by hand from what the session and the records say, never produced by an arm.
Kinds of case (case sources of one component, reported separately):
  hierarchy  the nesting of solutions, with a sub-agent that has no solution and two agents on one solution.
  agent      the solution each sub-agent is on, its state and its latest activity.
  collapsed  nothing of the records' fields is in the data until a solution is opened.
  expanded   the named fields and the connections with their fields, for only the solution that was opened.
  unknown    a solution id the records lack, and no records at all.

    python3 evaluation/structure_in_view/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def case(name, kind, rule, args, expect):
    return {"id": "structure-" + name, "kind": kind, "origin": "rule: " + rule, "args": dict(args), "expect": expect}


CASES = [
    case("hierarchy-nesting", "hierarchy", "a solution sits under the solution of its parent agent", {"check": "outline", "events": "session", "records": "tables"},
         {"outline": ["root-sol", "  child-a", "    ghost-sol", "  child-b"]}),
    case("hierarchy-without-records", "hierarchy", "the nesting does not depend on the records", {"check": "outline", "events": "session", "records": "none"},
         {"outline": ["root-sol", "  child-a", "    ghost-sol", "  child-b"]}),
    case("hierarchy-no-solution-agent", "hierarchy", "a sub-agent with no solution is listed apart and is not a node", {"check": "unplaced", "events": "session", "records": "tables"},
         {"unplaced": ["helper-x"]}),
    case("hierarchy-two-agents-one-node", "hierarchy", "two agents on one solution are one node with both agents", {"check": "agents_of", "events": "two_agents", "records": "tables", "solution": "child-a"},
         {"agents": ["r1", "r2"], "nodes": ["root-sol", "child-a"]}),
    case("hierarchy-no-events", "hierarchy", "no events give an empty tree", {"check": "outline", "events": "none", "records": "tables"}, {"outline": []}),
    case("agent-solution-of-each", "agent", "each sub-agent is on the solution it was started for", {"check": "agents_of", "events": "session", "records": "tables", "solution": "child-b"},
         {"agents": ["root-sol-child-b"], "nodes": ["root-sol", "child-a", "ghost-sol", "child-b"]}),
    case("agent-state-and-activity", "agent", "a node shows its agent's state and the latest step of the agent", {"check": "node", "events": "session", "records": "tables", "solution": "child-a",
                                                                                                          "paths": ["state", "activity", "agents.0.state"]},
         {"state": "running", "activity": "a.py (done)", "agents.0.state": "running"}),
    case("agent-unmet-state", "agent", "an agent that ended unmet makes its node unmet", {"check": "node", "events": "session", "records": "tables", "solution": "child-b", "paths": ["state", "agents.0.calls"]},
         {"state": "unmet", "agents.0.calls": 2}),
    case("agent-names-from-records", "agent", "a known solution shows its display name and an unknown one its id", {"check": "node", "events": "session", "records": "tables",
                                                                                                                  "solution": "child-a", "paths": ["name", "known"]},
         {"name": "Child A", "known": True}),
    case("collapsed-no-detail", "collapsed", "with nothing opened no node has detail and no field text is in the data", {"check": "collapsed", "events": "session", "records": "tables"},
         {"nodes_with_detail": 0, "field_text_found": []}),
    case("collapsed-expandable", "collapsed", "a known solution says it can be opened, an unknown one does not", {"check": "node", "events": "session", "records": "tables", "solution": "ghost-sol",
                                                                                                          "paths": ["expandable", "expanded"]},
         {"expandable": False, "expanded": False}),
    case("expanded-fields", "expanded", "an opened solution carries purpose, approach, metric with its latest value, selected implementation and milestones",
         {"check": "node", "events": "session", "records": "tables", "expanded": ["root-sol"], "solution": "root-sol",
          "paths": ["detail.fields.purpose", "detail.fields.approach", "detail.fields.metric.name", "detail.fields.metric.latest.balanced", "detail.fields.metric.latest.impl",
                    "detail.fields.selected.name", "detail.fields.milestones.0.text", "detail.fields.milestones.0.met", "detail.fields.milestones.1.met"]},
         {"detail.fields.purpose": "Root purpose text.", "detail.fields.approach": "Root approach text.", "detail.fields.metric.name": "Root Metric",
          "detail.fields.metric.latest.balanced": "0.91", "detail.fields.metric.latest.impl": "arm_a", "detail.fields.selected.name": "Arm A Name",
          "detail.fields.milestones.0.text": "First goal", "detail.fields.milestones.0.met": True, "detail.fields.milestones.1.met": False}),
    case("expanded-problems-and-ideals", "expanded", "an opened solution carries its problems and ideals with their fields", {"check": "node", "events": "session", "records": "tables",
                                                                                                                               "expanded": ["root-sol"], "solution": "root-sol",
                                                                                                                               "paths": ["detail.connections.problems.0.name", "detail.connections.problems.0.problem",
                                                                                                                                         "detail.connections.problems.0.why_it_matters", "detail.connections.problems.1.known",
                                                                                                                                         "detail.connections.ideals.0.principle", "detail.connections.ideals.0.state_description"]},
         {"detail.connections.problems.0.name": "Problem One", "detail.connections.problems.0.problem": "Problem one text.", "detail.connections.problems.0.why_it_matters": "Problem one matters.",
          "detail.connections.problems.1.known": False, "detail.connections.ideals.0.principle": "Ideal one principle.", "detail.connections.ideals.0.state_description": "Ideal one state."}),
    case("expanded-delegates", "expanded", "an opened solution carries the solutions it delegates to with their fields", {"check": "node", "events": "session", "records": "tables",
                                                                                                                        "expanded": ["root-sol"], "solution": "root-sol",
                                                                                                                        "paths": ["detail.connections.delegates.0.name", "detail.connections.delegates.0.purpose",
                                                                                                                                  "detail.connections.delegates.1.approach", "detail.connections.delegates.2.known"]},
         {"detail.connections.delegates.0.name": "Child A", "detail.connections.delegates.0.purpose": "Child A purpose text.", "detail.connections.delegates.1.approach": "Child B approach text.",
          "detail.connections.delegates.2.known": False}),
    case("expanded-only-the-opened", "expanded", "opening one solution leaves the others collapsed", {"check": "expanded_ids", "events": "session", "records": "tables", "expanded": ["child-a"]},
         {"expanded": ["child-a"], "nodes_with_detail": 1}),
    case("expanded-all", "expanded", "the star opens every known and unknown node", {"check": "expanded_ids", "events": "session", "records": "tables", "expanded": ["*"]},
         {"expanded": ["root-sol", "child-a", "ghost-sol", "child-b"], "nodes_with_detail": 4}),
    case("unknown-solution", "unknown", "an id the records lack is shown by its id and listed as unknown", {"check": "node", "events": "session", "records": "tables", "solution": "ghost-sol",
                                                                                                          "paths": ["name", "known", "state"]},
         {"name": "ghost-sol", "known": False, "state": "met"}),
    case("unknown-listed", "unknown", "the unknown ids are listed once", {"check": "top", "events": "session", "records": "tables", "paths": ["unknown"]}, {"unknown": ["ghost-sol"]}),
    case("unknown-opened", "unknown", "opening an unknown solution says there is no record and raises nothing", {"check": "node", "events": "session", "records": "tables",
                                                                                                                 "expanded": ["ghost-sol"], "solution": "ghost-sol",
                                                                                                                 "paths": ["detail.known", "detail.note", "detail.fields"]},
         {"detail.known": False, "detail.note": "no record for this solution", "detail.fields": {}}),
    case("unknown-no-records", "unknown", "with no records every solution is unknown and opening one is safe", {"check": "top", "events": "session", "records": "none", "expanded": ["root-sol"],
                                                                                                                 "paths": ["unknown", "expanded"]},
         {"unknown": ["child-a", "child-b", "ghost-sol", "root-sol"], "expanded": ["root-sol"]}),
]

if __name__ == "__main__":
    (HERE / "cases.json").write_text(json.dumps(CASES, indent=1) + "\n")
    print(len(CASES), "cases")
