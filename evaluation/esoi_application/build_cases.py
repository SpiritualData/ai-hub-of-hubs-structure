"""Rebuild cases.json for ESOI Application: a small set of written records (specs, metrics and one quality profile) and a proposed change, with the expected
result of applying it and the expected records afterwards. Ten cases: four edits that must apply (a spec, a metric and a quality profile field, and a second
edit of one record), and six that must be refused (unknown target, unknown field, unknown kind, empty value, an em dash, and a change with no target) and leave
every record as it was.

    python3 evaluation/esoi_application/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EM_DASH = "—"
RECORDS = {"solutions": {"role-writer": {"purpose": "Write the answer.", "out_of_scope": "Nothing.", "description": "Writes answers."}},
           "metrics": {"metric-cited": {"purpose": "Answers cite sources.", "record": "No run yet."}},
           "profiles": {"profile-p1": {"concision": "long", "tone": "plain"}}}


def after(table, target, field, value):
    changed = json.loads(json.dumps(RECORDS))
    changed[table][target][field] = value
    return changed


def location_cases():
    """The records-location port: the same edits against other locations. Ensure-one additions (a record, a milestone) that create once and leave a repeat alone,
    an edit a location holds for a person's approval (reported as proposed, records unchanged), and a location that refuses (reported plainly, records unchanged)."""
    add = {"kind": "record_add", "table": "implementations", "key": "post-a", "fields": {"name": "Post A", "description": "Hypothesis: a short post draws more clicks."}}
    milestone = {"kind": "milestone_add", "target": "role-writer", "key": "Writers are measured.", "fields": {"metric": "metric-cited"}}
    seeded = json.loads(json.dumps(RECORDS))
    seeded["solutions"]["role-writer"]["milestones"] = "Answers exist."
    withdraft = json.loads(json.dumps(RECORDS))
    withdraft.setdefault("implementations", {})["post-a"] = add["fields"]
    cases = [
        {"id": "location-adds-one-record", "kind": "adds", "args": {"records": RECORDS, "changes": [{"edit": add}]},
         "expect": {"result": {"applied": True, "table": "implementations", "target": "post-a", "fields": add["fields"], "created": True}, "records": withdraft}},
        {"id": "location-repeat-adds-nothing", "kind": "repeats", "args": {"records": RECORDS, "changes": [{"edit": add}, {"edit": add}]},
         "expect": {"result": {"applied": True, "table": "implementations", "target": "post-a", "fields": add["fields"], "created": False, "note": "already there"}, "records": withdraft}},
        {"id": "location-milestone-once", "kind": "repeats", "args": {"records": seeded, "changes": [{"edit": milestone}, {"edit": milestone}]},
         "expect": {"result": {"applied": True, "table": "solutions", "target": "role-writer", "field": "milestones", "after": "Writers are measured.", "created": False, "note": "already there"},
                    "records": json.loads(json.dumps(seeded).replace("Answers exist.", "Answers exist.\\nWriters are measured."))}},
        {"id": "location-refuses-empty-key", "kind": "refused", "args": {"records": RECORDS, "changes": [{"edit": dict(add, key="")}]},
         "expect": {"result": {"applied": False, "reason": "an addition needs a key that says which record it is, so a repeat adds nothing"}, "records": RECORDS}},
        {"id": "location-holds-edit-for-approval", "kind": "proposed", "args": {"records": RECORDS, "source": {"holds": ["purpose"]}, "changes": [{"edit": {"kind": "spec_edit", "target": "role-writer", "field": "purpose", "value": "State it first."}}]},
         "expect": {"result": {"applied": False, "proposed": True, "table": "solutions", "target": "role-writer", "field": "purpose", "decision": "decision-1",
                               "reason": "proposed, waiting for approval: the owner has to say yes"}, "records": RECORDS}},
        {"id": "location-denies-plainly", "kind": "refused", "args": {"records": RECORDS, "source": {"denies": "you may not change this specification"}, "changes": [{"edit": {"kind": "spec_edit", "target": "role-writer", "field": "purpose", "value": "State it first."}}]},
         "expect": {"result": {"applied": False, "reason": "you may not change this specification"}, "records": RECORDS}}]
    return cases


def main():
    cases = []
    for name, kind, table, target, field, value in (
            ("spec-purpose", "spec_edit", "solutions", "role-writer", "purpose", "State what the answer is for first."),
            ("metric-record", "metric_edit", "metrics", "metric-cited", "record", "The share of answers with a cited source."),
            ("profile-concision", "quality_profile_edit", "profiles", "profile-p1", "concision", "short"),
            ("spec-out-of-scope", "spec_edit", "solutions", "role-writer", "out_of_scope", "Choosing the topic.")):
        before = RECORDS[table][target][field]
        cases.append({"id": "apply-" + name, "kind": "applies", "args": {"records": RECORDS, "change": {"edit": {"kind": kind, "target": target, "field": field, "value": value}}},
                      "expect": {"result": {"applied": True, "table": table, "target": target, "field": field, "before": before, "after": value}, "records": after(table, target, field, value)}})
    for name, edit, why in (
            ("unknown-target", {"kind": "spec_edit", "target": "role-missing", "field": "purpose", "value": "x"}, "no solutions record named 'role-missing'"),
            ("unknown-field", {"kind": "spec_edit", "target": "role-writer", "field": "colour", "value": "x"}, "solutions record 'role-writer' has no field 'colour'"),
            ("unknown-kind", {"kind": "prompt_edit", "target": "role-writer", "field": "purpose", "value": "x"}, "the change kind 'prompt_edit' is not an edit to a spec, a metric or a quality profile"),
            ("empty-value", {"kind": "spec_edit", "target": "role-writer", "field": "purpose", "value": "  "}, "the new value is empty"),
            ("em-dash", {"kind": "spec_edit", "target": "role-writer", "field": "purpose", "value": "Write " + EM_DASH + " briefly."}, "the new value carries an em dash"),
            ("no-target", {"kind": "metric_edit", "field": "record", "value": "x"}, "no metrics record named None")):
        cases.append({"id": "apply-refused-" + name, "kind": "refused", "args": {"records": RECORDS, "change": {"edit": edit}},
                      "expect": {"result": {"applied": False, "reason": why}, "records": RECORDS}})
    cases += location_cases()
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
