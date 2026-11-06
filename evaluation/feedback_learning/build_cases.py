"""Rebuild cases.json for Feedback Learning: written feedback from a person and the edit a careful reader would propose from it, or the reason none can be
proposed. Nineteen cases: six corrections that name a record, a field and a new value (a spec, a metric and a quality profile), two that name a person so the edit
is scoped to them, and four that are too vague, name nothing or concern something that is not a record, which must come back unresolved, and seven reports of a turn that ended badly (one per signal, two together, a turn handled well and one with no input) that become a proposed new case or come back unresolved.

    python3 evaluation/feedback_learning/build_cases.py

Standard library only."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def edit(kind, target, field, value, person, text):
    return {"edit": {"kind": kind, "target": target, "field": field, "value": value, "scope": person, "reason": text}, "person": person}


def main():
    cases = []
    for name, person, feedback in (
            ("spec-purpose", "p1", {"text": "say what it is for first", "about": "role-writer", "field": "purpose", "to": "State what the answer is for in its first sentence."}),
            ("spec-out-of-scope", "p2", {"text": "not your job", "about": "role-writer", "field": "out_of_scope", "to": "Choosing the topic of the request."}),
            ("metric-record", "p1", {"text": "count only cited answers", "about": "metric-cited", "field": "record", "to": "The share of answers with a cited source.", "concerns": "metric"}),
            ("metric-purpose", "p3", {"text": "stricter", "about": "metric-cited", "field": "purpose", "to": "Every claim has a source.", "concerns": "metric"}),
            ("profile-concision", "p1", {"text": "too long", "about": "profile-p1", "field": "concision", "to": "short", "concerns": "quality_profile"}),
            ("profile-tone", "p2", {"text": "warmer please", "about": "profile-p2", "field": "tone", "to": "warm", "concerns": "quality_profile"})):
        cases.append({"id": "learn-" + name, "kind": "named", "args": {"person": person, "feedback": feedback},
                      "expect": edit({"spec": "spec_edit"}.get(feedback.get("concerns", "spec"), {"metric": "metric_edit", "quality_profile": "quality_profile_edit"}.get(feedback.get("concerns"), "")),
                                     feedback["about"], feedback["field"], feedback["to"], person, feedback["text"])})
    for name, person, feedback in (
            ("scoped-to-first-person", "alice", {"text": "shorter", "about": "profile-alice", "field": "concision", "to": "short", "concerns": "quality_profile"}),
            ("scoped-to-second-person", "bob", {"text": "longer", "about": "profile-bob", "field": "concision", "to": "long", "concerns": "quality_profile"})):
        cases.append({"id": "learn-" + name, "kind": "scoped", "args": {"person": person, "feedback": feedback},
                      "expect": edit("quality_profile_edit", feedback["about"], feedback["field"], feedback["to"], person, feedback["text"])})
    for name, person, feedback, why in (
            ("no-target", "p1", {"text": "that was wrong", "field": "purpose", "to": "x"}, "the feedback does not say what it concerns"),
            ("no-value", "p1", {"text": "change the purpose", "about": "role-writer", "field": "purpose"}, "the feedback does not say the new value"),
            ("only-text", "p1", {"text": "I did not like it"}, "the feedback does not say what it concerns or the field or the new value"),
            ("not-a-record", "p1", {"text": "be nicer", "about": "the weather", "field": "tone", "to": "nice", "concerns": "weather"},
             "the feedback concerns weather, which is not a spec, a metric or a quality profile")):
        cases.append({"id": "learn-unresolved-" + name, "kind": "unresolved", "args": {"person": person, "feedback": feedback},
                      "expect": {"edit": None, "person": person, "unresolved": why}})
    for name, input_text, signals, expect_signals in (
            ("unmet", "what should the team do next?", {"unmet": True}, ["unmet"]),
            ("error", "send me the notes", {"error": True}, ["error"]),
            ("empty-reply", "any updates?", {"empty_reply": True}, ["empty_reply"]),
            ("pushed-back", "summarise the call", {"pushed_back": True, "unmet": False}, ["pushed_back"]),
            ("unhappy-and-unmet", "plan the week", {"unhappy_followup": True, "unmet": True}, ["unmet", "unhappy_followup"])):
        case = {"case_id": "CAND-" + hashlib.sha1(input_text.encode("utf-8")).hexdigest()[:10], "input": input_text, "signals": expect_signals,
                "reason": ", ".join(expect_signals), "timestamp": "2026-01-01T00:00:00Z"}
        cases.append({"id": "learn-noticed-" + name, "kind": "noticed", "args": {"person": "p1", "feedback": {"input": input_text, "signals": signals, "at": "2026-01-01T00:00:00Z"}},
                      "expect": {"edit": {"kind": "dataset_case_add", "target": "poorly_answered_inputs", "field": "cases", "value": case, "scope": "p1", "reason": case["reason"]}, "person": "p1"}})
    for name, feedback, why in (
            ("handled-well", {"input": "hello", "signals": {"unmet": False, "error": False}}, "no signal says the input was handled badly"),
            ("no-input", {"signals": {"error": True}}, "the feedback does not say what was asked")):
        cases.append({"id": "learn-noticed-unresolved-" + name, "kind": "noticed", "args": {"person": "p1", "feedback": feedback}, "expect": {"edit": None, "person": "p1", "unresolved": why}})
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
