"""Rebuild cases.json for Prioritization from the ordering rules that Quest and Quest AI Runner (QAR) state in their own code and tests. Each case names its
source and whether its candidates are the test's own data (``verbatim``) or written to exercise a rule the source states (``rule``). The expected order is
written by hand from the stated rule, never produced by an arm.

Sources (paths are inside the Quest repositories):
  quest list     quest-backend ``order_quests_by_user_priority`` and the ``priority`` and ``priority_by_user`` fields of the quest model: ranked ascending first
                 (0 is highest), then unranked in the order given; a person's own entry in ``priority_by_user``, else the legacy ``priority`` only for the quest's
                 creator. Test data: ``tests/test_quest_ranking_all.py`` (the cap keeps the highest priority quests) and ``tests/business/test_accessible_quests.py``
                 (a member ranks a team quest above their own).
  work order     quest-backend ``prompts/autopilot_prompts.py``, the default quest instructions: the open asks first, then the goals of the periods running now,
                 shortest horizon first (today, this week, this month, the quarter, the year), then anything the run thought of itself.
  goal ladder    QAR ``autopilot_periods._ladder_order_key``: inside a horizon nearest deadline first, undated last, payload order breaks ties. Test data:
                 ``tests/test_autopilot_goal_ladder.py``.
  open asks      QAR ``quest_asks_brief.asks_brief_section``: open asks ordered by when they were asked, oldest first. Test data: ``tests/test_quest_asks_brief.py``.

    python3 evaluation/prioritization/build_cases.py

Standard library only. No case covers a person's explicit order, deferral, feedback or ``not_before``: no repository holds real ordered examples of those, so the
unit tests of the seat cover them and this metric does not."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-07-12T09:00:00Z"


def case(name, source, origin, person, candidates, expect, now=NOW):
    return {"id": "prioritize-" + name, "kind": source, "origin": origin, "args": {"person": person, "candidates": candidates, "now": now}, "expect": expect}


def quest(ident, **fields):
    return dict({"id": ident, "kind": "quest"}, **fields)


def main():
    cases = []
    # quest list: test data
    fifty = [quest(f"q{i}", rank=i, owner="u") for i in range(50)]
    cases.append(case("quest-cap-keeps-highest-priority", "quest-list", "verbatim test_quest_ranking_all.py", "u", fifty, [f"q{i}" for i in range(50)]))
    cases.append(case("quest-member-ranks-team-quest-above-own", "quest-list", "verbatim test_accessible_quests.py", "member",
                      [quest("member-quest", owner="member", rank_by_person={"member": 1}), quest("team-quest", owner="creator", rank_by_person={"member": 0})],
                      ["team-quest", "member-quest"]))
    # quest list: the stated rule
    cases.append(case("quest-unranked-after-ranked", "quest-list", "rule order_quests_by_user_priority", "u",
                      [quest("u1", owner="u"), quest("r2", owner="u", rank=2), quest("r0", owner="u", rank=0), quest("u2", owner="u")], ["r0", "r2", "u1", "u2"]))
    cases.append(case("quest-legacy-rank-is-the-creators-only", "quest-list", "rule priority field of the quest model", "p",
                      [quest("other-creators", owner="o", rank=0), quest("mine", owner="p", rank=3)], ["mine", "other-creators"]))
    cases.append(case("quest-own-entry-beats-legacy-rank", "quest-list", "rule priority_by_user field of the quest model", "p",
                      [quest("y", owner="o", rank=0, rank_by_person={"p": 5}), quest("x", owner="p", rank=3)], ["x", "y"]))
    # work order: the stated rule
    cases.append(case("work-asks-then-horizons-then-ideas", "work-order", "rule default quest instructions", "",
                      [{"id": "i1", "kind": "idea"}, {"id": "g-year", "kind": "goal", "horizon": "year"}, {"id": "g-today", "kind": "goal", "horizon": "today"},
                       {"id": "a1", "kind": "ask"}, {"id": "g-week", "kind": "goal", "horizon": "week"}], ["a1", "g-today", "g-week", "g-year", "i1"]))
    cases.append(case("work-asks-keep-the-order-given", "work-order", "rule default quest instructions", "",
                      [{"id": "g-today", "kind": "goal", "horizon": "today"}, {"id": "a1", "kind": "ask"}, {"id": "a2", "kind": "ask"}], ["a1", "a2", "g-today"]))
    cases.append(case("work-month-before-quarter", "work-order", "rule default quest instructions", "",
                      [{"id": "g-quarter", "kind": "goal", "horizon": "quarter"}, {"id": "g-month", "kind": "goal", "horizon": "month"}], ["g-month", "g-quarter"]))
    cases.append(case("work-a-goal-before-an-idea", "work-order", "rule default quest instructions", "",
                      [{"id": "i1", "kind": "idea"}, {"id": "g-quarter", "kind": "goal", "horizon": "quarter"}], ["g-quarter", "i1"]))
    # goal ladder: test data
    month = [{"id": f"m{i}", "kind": "goal", "horizon": "month", "deadline": f"2026-07-{i:02d}"} for i in range(20, 8, -1)]
    cases.append(case("ladder-nearest-deadline-first", "goal-ladder", "verbatim test_autopilot_goal_ladder.py", "", month, [f"m{i}" for i in range(9, 21)]))
    cases.append(case("ladder-undated-last-in-plan-order", "goal-ladder", "verbatim test_autopilot_goal_ladder.py", "",
                      [{"id": "m1", "kind": "goal", "horizon": "month"}, {"id": "m2", "kind": "goal", "horizon": "month", "deadline": "2026-07-30"},
                       {"id": "m3", "kind": "goal", "horizon": "month"}, {"id": "m4", "kind": "goal", "horizon": "month", "deadline": "2026-07-14"}],
                      ["m4", "m2", "m1", "m3"]))
    # open asks: test data
    cases.append(case("asks-oldest-first", "open-asks", "test data of test_quest_asks_brief.py, listed newest first", "",
                      [{"id": "k_new", "kind": "ask", "asked_at": "2026-10-15T09:00:00Z"}, {"id": "k_open", "kind": "ask", "asked_at": "2026-10-12T12:00:00Z"}],
                      ["k_open", "k_new"]))
    # the two stated rules together: the horizon decides before the deadline
    cases.append(case("work-horizon-before-deadline", "work-order", "rule default quest instructions with the goal ladder", "",
                      [{"id": "g-week-late", "kind": "goal", "horizon": "week", "deadline": "2026-07-18"}, {"id": "g-today", "kind": "goal", "horizon": "today", "deadline": "2026-07-13"}],
                      ["g-today", "g-week-late"]))
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
