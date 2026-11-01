"""The work trace contract: the allowlist projector, the validator and the emitting helper. No network, no model."""
import json

import pytest

from hubofhubs.ports import events, trace
from hubofhubs.ports.trace import WorkTrace, WorkTraceError, project, validate


def raw(**over):
    base = {"step_id": "web-1", "solution_id": "search-backend", "kind": "sources", "label_key": "workTrace.web.reading",
            "state": "running", "counts": {"found": 3, "read": 2}, "affects_user": False,
            "items": [{"url": "https://www.Example.org/a/b?token=SECRET#x", "label": "A page — Example"}]}
    base.update(over)
    return base


def test_constant_is_live_only():
    assert events.EVENT_WORK_TRACE == "work_trace"
    assert events.EVENT_WORK_TRACE not in events.SURFACING_EVENTS


def test_projector_drops_every_field_off_the_allowlist():
    event = project(raw(query="private question", snippet="page text", reasoning="because", tool_args={"q": 1},
                        path="/etc/passwd"), trace_id="t1").to_dict()
    assert set(event) == {"v", "trace_id", "step_id", "solution_id", "kind", "label_key", "state", "counts", "items",
                          "affects_user", "started_at"}
    assert "private question" not in json.dumps(event) and "SECRET" not in json.dumps(event)
    assert validate(event) == []


def test_sources_are_domains_only_and_em_dash_free():
    item = project(raw(), trace_id="t1").items[0]
    assert item == {"ref": "example.org", "label": "A page, Example"}


def test_url_inside_a_label_becomes_a_domain():
    event = project(raw(kind="papers", items=[{"ref": "W1", "label": "See https://a.example.com/x?y=1 now", "sub": "Lee et al., 2021"}]),
                    trace_id="t1")
    assert event.items[0]["label"] == "See a.example.com now"
    assert event.items[0]["sub"] == "Lee et al., 2021"


def test_paths_are_dropped_and_labels_trimmed():
    event = project(raw(kind="records", items=[{"ref": "/home/user/file", "label": "f"}, {"ref": "r1", "label": "x" * 200, "kind": "quest"},
                                              {"ref": "r2", "label": "line\nbreak"}]), trace_id="t1")
    assert len(event.items) == 2 and event.items[0]["ref"] == "r1"
    assert len(event.items[0]["label"]) == trace.MAX_LABEL and event.items[0]["kind"] == "quest"
    assert "\n" not in event.items[1]["label"]


def test_items_capped():
    many = [{"url": f"https://s{i}.example.org/p"} for i in range(50)]
    assert len(project(raw(items=many), trace_id="t1").items) == trace.MAX_ITEMS


def test_records_are_counts_only_for_a_viewer_who_may_not_see_titles():
    event = project(raw(kind="records", counts={}, items=[{"ref": "q1", "label": "My private goal"}] * 3),
                    trace_id="t1", viewer_may_see_titles=False)
    assert event.items == [] and event.counts == {"found": 3}
    assert "private" not in json.dumps(event.to_dict())


@pytest.mark.parametrize("bad", [dict(state="paused"), dict(label_key="Reading the web now"), dict(step_id=""),
                                 dict(solution_id="a b"), dict(kind="Not A Slug")])
def test_bad_values_rejected(bad):
    with pytest.raises(WorkTraceError):
        project(raw(**bad), trace_id="t1")
    assert trace.project_or_none(raw(**bad), trace_id="t1") is None


def test_counts_allowlist_and_unknown_kind_kept():
    event = project(raw(kind="future_kind", counts={"found": "4", "read": -1, "secret": 9, "total": True}), trace_id="t1")
    assert event.counts == {"found": 4} and event.kind == "future_kind"


def test_done_gets_ended_at_and_running_does_not():
    assert project(raw(), trace_id="t1").ended_at is None
    assert project(raw(state="done"), trace_id="t1").ended_at


def test_validate_flags_leaks():
    event = project(raw(), trace_id="t1").to_dict()
    event["extra"] = 1
    event["items"][0]["label"] = "https://x.org/p"
    assert len(validate(event)) == 2


def test_helper_coalesces_but_always_sends_final_and_replaces_by_step():
    sent, clock = [], [0.0]
    wt = WorkTrace(sent.append, trace_id="t1", clock=lambda: clock[0])
    for n in range(10):
        wt.update("web-1", solution_id="search-backend", kind="sources", label_key="workTrace.web.reading", counts={"read": n})
        clock[0] += 0.05
    assert 1 <= len(sent) <= 3
    wt.update("web-1", solution_id="search-backend", kind="sources", label_key="workTrace.web.reading", state="done", counts={"read": 10})
    assert sent[-1].data["state"] == "done" and sent[-1].data["counts"] == {"read": 10}
    assert sent[-1].type == events.EVENT_WORK_TRACE
    assert [e["counts"] for e in wt.summary()] == [{"read": 10}]
    assert sent[-1].data["started_at"] == sent[0].data["started_at"]


def test_helper_text_changes_with_state_and_failing_emit_is_swallowed():
    def boom(_):
        raise RuntimeError("stream dropped")
    wt = WorkTrace(boom, trace_id="t1")
    assert wt.update("s", solution_id="x", kind="check", label_key="workTrace.check", state="done") is not None
    a = trace.progress_event(project(raw(), trace_id="t1")).text
    b = trace.progress_event(project(raw(state="done"), trace_id="t1")).text
    assert a != b


def test_running_step_left_out_of_summary_and_bad_event_never_raises():
    wt = WorkTrace(lambda e: None, trace_id="t1")
    wt.update("a", solution_id="x", kind="check", label_key="workTrace.check")
    assert wt.update("b", solution_id="x", kind="check", label_key="not a key") is None
    assert wt.summary() == []


def test_action_titles_are_also_counts_only_for_a_viewer_who_may_not_see_them():
    event = project(raw(kind="action", counts={}, items=[{"ref": "q1", "label": "Private goal"}]), trace_id="t1",
                    viewer_may_see_titles=False)
    assert event.items == [] and event.counts == {"found": 1}


def test_redacting_an_already_projected_event_is_stable():
    full = project(raw(kind="records", counts={"found": 2, "read": 2}, items=[{"ref": "a", "label": "A"}, {"ref": "b", "label": "B"}]),
                   trace_id="t1").to_dict()
    again = project(full, viewer_may_see_titles=False).to_dict()
    assert again["items"] == [] and again["counts"] == {"found": 2, "read": 2} and again["started_at"] == full["started_at"]
    assert validate(again) == []


def test_a_sources_item_keeps_whether_the_page_was_read_or_only_found():
    from hubofhubs.ports.trace import project_item
    assert project_item({"ref": "https://a.example/x?q=1", "label": "A", "kind": "read"}, "sources") == {"ref": "a.example", "label": "A", "kind": "read"}
    assert project_item({"ref": "b.example", "kind": "found"}, "sources") == {"ref": "b.example", "label": "b.example", "kind": "found"}
    assert "kind" not in project_item({"ref": "c.example", "kind": "weird"}, "sources")
