"""Feedback Learning: turns one person's feedback into a proposed edit to a spec or a metric (or to their quality profile), kept for that person and
never written into a prompt. ESOI Application applies the proposal; Judgment Calls decides whether anyone is asked first. Standard library plus
``esoi``."""
import hashlib
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

KINDS = {"spec": "spec_edit", "metric": "metric_edit", "quality_profile": "quality_profile_edit"}
#: The structured facts of a turn that mean an input was handled badly, as the consumer reports them (booleans, never read from the words of a reply).
SIGNALS = ("unmet", "error", "empty_reply", "pushed_back", "unhappy_followup")


@implementation("feedback-learning", "scoped_record_edit")
class ScopedRecordEdit:
    """A correction that names what it concerns (``about``: a record id; ``field``; ``to``: the new value) becomes one edit to that record, scoped to the
    person who gave it. Feedback that names no target or no new value is returned unresolved with what is missing, because guessing an edit would
    change behaviour for someone on a misreading. A turn reported as handled badly (``signals``) becomes a proposed new case instead (``noticed``)."""
    REQUIRES = ()     # nothing

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        feedback = dict(feedback or {})
        if feedback.get("signals") is not None and not feedback.get("about"):
            return self.noticed(person, feedback)
        missing = [name for name, key in (("what it concerns", "about"), ("the field", "field"), ("the new value", "to")) if not str(feedback.get(key) or "").strip()]
        if missing:
            return {"edit": None, "person": person, "unresolved": "the feedback does not say " + " or ".join(missing)}
        kind = KINDS.get(str(feedback.get("concerns") or "spec"))
        if kind is None:
            return {"edit": None, "person": person, "unresolved": "the feedback concerns " + str(feedback["concerns"]) + ", which is not a spec, a metric or a quality profile"}
        return {"edit": {"kind": kind, "target": str(feedback["about"]), "field": str(feedback["field"]), "value": feedback["to"], "scope": person,
                         "reason": str(feedback.get("text") or "")}, "person": person}


    def noticed(self, person: str, feedback: Mapping[str, Any]) -> Mapping[str, Any]:
        """An input whose turn ended badly, reported through structured facts (``signals``: booleans for ``unmet`` goal, ``error``, ``empty_reply``,
        ``pushed_back`` work to the person that means could have done, ``unhappy_followup``), with the ``input`` asked and the ``dataset`` of badly handled
        inputs, becomes one proposed new case for a person to prioritise. No input, or no signal set, is unresolved: nothing is proposed for an input
        that was handled well."""
        text = str(feedback.get("input") or "").strip()
        raised = [name for name in SIGNALS if (feedback.get("signals") or {}).get(name) is True]
        if not text:
            return {"edit": None, "person": person, "unresolved": "the feedback does not say what was asked"}
        if not raised:
            return {"edit": None, "person": person, "unresolved": "no signal says the input was handled badly"}
        case = {"case_id": "CAND-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10], "input": text, "signals": raised,
                "reason": str(feedback.get("reason") or ", ".join(raised)), "timestamp": str(feedback.get("at") or "")}
        return {"edit": {"kind": "dataset_case_add", "target": str(feedback.get("dataset") or "poorly_answered_inputs"), "field": "cases", "value": case,
                         "scope": person, "reason": case["reason"]}, "person": person}


@implementation("feedback-learning", "kept_note")
class KeptNote:
    """Keeps the feedback text as a note for the next reply: the common way, which changes the next answer and proposes no edit, so the person gives the
    correction again once the note is gone."""
    REQUIRES = ()     # nothing

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        text = str((feedback or {}).get("text") or "")
        return {"edit": None, "person": person, "note": text}

