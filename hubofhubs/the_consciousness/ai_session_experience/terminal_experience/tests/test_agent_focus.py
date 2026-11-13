"""Going in and out of the agents of a run (agent_focus.py): the model every terminal arm shares, so it is tested once, with no screen."""
from hubofhubs.the_consciousness.ai_session_experience.session_events import MAIN, AgentEnded, AgentStarted, Steer, Stop, Usage
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import agent_focus
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView, frame


def tree(depth):
    view = SessionView()
    parent = MAIN
    for level in range(1, depth + 1):
        view.apply(AgentStarted(agent_id=f"a{level}", parent_id=parent, task=f"task number {level} with a long name"))
        parent = f"a{level}"
    return view


def test_enter_to_any_depth_and_one_key_up_a_level():
    view = tree(4)
    focus = view.focus
    for level in range(1, 5):
        assert agent_focus.enter(view, focus) == "" and focus.current == f"a{level}"
    assert agent_focus.enter(view, focus) == "No helper here to enter."          # the deepest has none below
    for level in range(3, 0, -1):
        assert agent_focus.leave(focus) and focus.current == f"a{level}"
    assert agent_focus.leave(focus) and focus.current == MAIN and not agent_focus.leave(focus)


def test_the_breadcrumb_is_never_wider_than_the_room_and_keeps_where_you_are():
    view = tree(4)
    agent_focus.focus_on(view, view.focus, "a4")
    for width in (120, 56, 30):
        row = agent_focus.breadcrumb(view, view.focus, width)
        assert len(row) <= width and row.startswith(("Main", "...")) and "task number 4" in row[:width] or width == 30
    assert agent_focus.focus_on(view, view.focus, "nothing") is False and view.focus.current == "a4"
    assert agent_focus.focus_on(view, view.focus, "") and view.focus.path == []


def test_a_typed_line_and_escape_are_aimed_at_the_agent_in_view_and_at_the_top_at_the_run():
    view = tree(2)
    focus = view.focus
    assert agent_focus.steer_for(focus, "hello", "m1") == Steer(text="hello", agent_id="", message_id="m1") and agent_focus.stop_for(focus) == Stop(agent_id="")
    agent_focus.enter(view, focus)
    agent_focus.enter(view, focus)
    assert agent_focus.steer_for(focus, "hello", "m2").agent_id == "a2" and agent_focus.stop_for(focus).agent_id == "a2"


def test_the_view_of_a_helper_has_the_same_shape_at_depth_one_and_four_and_a_finished_one_stays_listed():
    shapes = []
    for depth in (1, 4):
        view = tree(depth)
        view.apply(Usage(agent_id=f"a{depth}", tokens=2000, calls=3))
        agent_focus.focus_on(view, view.focus, f"a{depth}")
        rows = frame(view, width=80)
        shapes.append((len(rows), [len(r) - len(r.lstrip()) for r in rows if "task number" in r], rows[-2][:20]))
    assert shapes[0][0] == shapes[1][0] and max(shapes[1][1]) <= max(shapes[0][1]) + 2 and shapes[0][2] == shapes[1][2]       # the same rows, no indentation per level, the same keys
    view = tree(2)
    view.apply(AgentEnded(agent_id="a2", state="met", summary="two finds", tokens=1500))
    agent_focus.focus_on(view, view.focus, "a1")
    rows = "\n".join(agent_focus.child_rows(view, view.focus, 80))
    assert "task number 2" in rows and "Done:" in rows and "two finds" in rows and rows.count("two finds") == 1
    agent_focus.enter(view, view.focus)
    assert "Result: two finds" in "\n".join(agent_focus.agent_lines(view, view.focus, 80))
