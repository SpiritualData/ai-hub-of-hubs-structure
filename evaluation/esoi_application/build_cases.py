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
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
