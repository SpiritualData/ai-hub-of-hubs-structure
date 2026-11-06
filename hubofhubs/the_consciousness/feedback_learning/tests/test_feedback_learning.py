"""Feedback Learning proposes one scoped edit for feedback that names its target, and ESOI Application applies it through the Consciousness flow."""
from hubofhubs.the_consciousness.feedback_learning.propose import KeptNote, ScopedRecordEdit
from hubofhubs.the_consciousness.flow import ConsciousnessComposition
from hubofhubs.the_consciousness.judgment_calls.judgment import SeverityPolicy
from hubofhubs.the_intelligence.critical_thinking.esoi_application.apply import RecordFieldEdit

FEEDBACK = {"text": "too long", "about": "profile-p1", "field": "concision", "to": "short", "concerns": "quality_profile"}


def test_feedback_that_names_its_target_becomes_an_edit_scoped_to_the_person_and_vague_feedback_is_not_guessed_at():
    edit = ScopedRecordEdit().learn("p1", FEEDBACK)["edit"]
    assert edit["scope"] == "p1" and edit["target"] == "profile-p1" and edit["kind"] == "quality_profile_edit"
    assert ScopedRecordEdit().learn("p1", {"text": "I did not like it"})["edit"] is None
    assert KeptNote().learn("p1", FEEDBACK)["edit"] is None


def test_a_correction_given_once_edits_the_profile_through_the_flow():
    esoi = RecordFieldEdit({"profiles": {"profile-p1": {"concision": "long"}}})
    out = ConsciousnessComposition(None, None, SeverityPolicy(), ScopedRecordEdit(), esoi, None).learn("p1", FEEDBACK)
    assert esoi.records["profiles"]["profile-p1"]["concision"] == "short" and out["steps"][-1]["status"] == "done"
