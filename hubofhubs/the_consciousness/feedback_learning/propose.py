"""Feedback Learning: turns one person's feedback into a proposed edit to a spec or a metric (or to their quality profile), kept for that person and
never written into a prompt. ESOI Application applies the proposal; Judgment Calls decides whether anyone is asked first. Standard library plus
``esoi``."""
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

KINDS = {"spec": "spec_edit", "metric": "metric_edit", "quality_profile": "quality_profile_edit"}


@implementation("feedback-learning", "scoped_record_edit")
class ScopedRecordEdit:
    """A correction that names what it concerns (``about``: a record id; ``field``; ``to``: the new value) becomes one edit to that record, scoped to the
    person who gave it. Feedback that names no target or no new value is returned unresolved with what is missing, because guessing an edit would
    change behaviour for someone on a misreading."""
    REQUIRES = ()     # nothing

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        feedback = dict(feedback or {})
        missing = [name for name, key in (("what it concerns", "about"), ("the field", "field"), ("the new value", "to")) if not str(feedback.get(key) or "").strip()]
        if missing:
            return {"edit": None, "person": person, "unresolved": "the feedback does not say " + " or ".join(missing)}
        kind = KINDS.get(str(feedback.get("concerns") or "spec"))
        if kind is None:
            return {"edit": None, "person": person, "unresolved": "the feedback concerns " + str(feedback["concerns"]) + ", which is not a spec, a metric or a quality profile"}
        return {"edit": {"kind": kind, "target": str(feedback["about"]), "field": str(feedback["field"]), "value": feedback["to"], "scope": person,
                         "reason": str(feedback.get("text") or "")}, "person": person}


@implementation("feedback-learning", "kept_note")
class KeptNote:
    """Keeps the feedback text as a note for the next reply: the common way, which changes the next answer and proposes no edit, so the person gives the
    correction again once the note is gone."""
    REQUIRES = ()     # nothing

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        text = str((feedback or {}).get("text") or "")
        return {"edit": None, "person": person, "note": text}
