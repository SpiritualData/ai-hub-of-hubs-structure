"""ESOI Application: applies one proposed change to the specs and metrics it is handed, as an edit to a record field and never as a longer prompt,
and says exactly what changed. Standard library plus ``esoi``."""
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import RecordsSource

EDITABLE = {"spec_edit": "solutions", "metric_edit": "metrics", "quality_profile_edit": "profiles", "problem_edit": "problems", "ideal_edit": "ideals",
            "implementation_edit": "implementations"}
ADDING = ("record_add", "milestone_add")
ADDABLE = ("problems", "ideals", "solutions", "implementations", "metrics")
EM_DASH = "—"


class TableRecords:
    """The default records location: tables held in memory, ``{table: {record id: {column: value}}}``, copied on construction so a refused or proposed
    change leaves the caller's records as they were. Writing them back to files is the caller's."""

    def __init__(self, records: Optional[Mapping[str, Mapping[str, Mapping[str, Any]]]] = None):
        self.tables = {table: {key: dict(row) for key, row in rows.items()} for table, rows in (records or {}).items()}

    def read(self, subject: str = "") -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        return self.tables

    def apply(self, edit: Mapping[str, Any]) -> Mapping[str, Any]:
        table, target = str(edit["table"]), str(edit["target"])
        rows = self.tables.setdefault(table, {})
        if edit["op"] == "set":
            row = rows[target]
            before = row[edit["field"]]
            row[edit["field"]] = edit["value"]
            return {"status": "applied", "before": before}
        if edit["op"] == "add":
            if target in rows:
                return {"status": "unchanged"}
            rows[target] = dict(edit["fields"])
            return {"status": "applied"}
        row = rows[target]     # a milestone: one more sentence in the solution's milestones text, once
        lines = [line for line in str(row.get("milestones") or "").split("\n") if line.strip()]
        if edit["key"] in lines:
            return {"status": "unchanged"}
        row["milestones"] = "\n".join(lines + [edit["key"]])
        return {"status": "applied"}


@implementation("esoi-application", "record_field_edit")
class RecordFieldEdit:
    """Sets the one field a change names on the one record it names, or adds one record or milestone once (ensure-one), in the table its kind belongs to
    (problems, ideals, solutions, implementations, metrics, quality profiles), at the records location it is given. It refuses a change whose target, field
    or kind does not exist, whose value is empty or carries an em dash, and says why; a refused change leaves every record as it was, and a change the
    location holds for a person's approval is reported as proposed, never as applied."""
    REQUIRES = ()     # the records are a constructor argument

    def __init__(self, records: Optional[Mapping[str, Mapping[str, Mapping[str, Any]]]] = None, source: Optional[RecordsSource] = None):
        self.source: RecordsSource = source if source is not None else TableRecords(records)

    @property
    def records(self) -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        return self.source.read("")

    def read(self, subject: str = "") -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        return self.source.read(subject)

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]:
        edit = dict(change.get("edit") or change)
        subject = str(change.get("subject") or edit.get("subject") or "")
        kind = str(edit.get("kind") or "")
        if kind in ADDING:
            return self.add(subject, kind, edit)
        table = EDITABLE.get(kind)
        if table is None:
            return refused("the change kind " + repr(edit.get("kind")) + " is not an edit to a spec, a metric or a quality profile")
        row = self.source.read(subject).get(table, {}).get(str(edit.get("target") or ""))
        if row is None:
            return refused("no " + table + " record named " + repr(edit.get("target")))
        field = str(edit.get("field") or "")
        if field not in row:
            return refused(table + " record " + repr(edit.get("target")) + " has no field " + repr(field))
        value = edit.get("value")
        if value is None or not str(value).strip():
            return refused("the new value is empty")
        if EM_DASH in str(value):
            return refused("the new value carries an em dash")
        answer = self.source.apply({"op": "set", "subject": subject, "table": table, "target": str(edit["target"]), "field": field, "value": value})
        return report(answer, {"table": table, "target": str(edit["target"]), "field": field, "after": value})

    def add(self, subject: str, kind: str, edit: Mapping[str, Any]) -> Mapping[str, Any]:
        """Ensure-one: the record (or milestone) named by ``key`` exists afterwards, created if it was not there and left alone if it was."""
        key = str(edit.get("key") or "").strip()
        fields = {str(name): value for name, value in dict(edit.get("fields") or {}).items()}
        if not key:
            return refused("an addition needs a key that says which record it is, so a repeat adds nothing")
        if any(value is None or not str(value).strip() for value in fields.values()):
            return refused("a new value is empty")
        if EM_DASH in key or any(EM_DASH in str(value) for value in fields.values()):
            return refused("the new value carries an em dash")
        if kind == "milestone_add":
            table, target = "solutions", str(edit.get("target") or "")
            if target not in self.source.read(subject).get(table, {}):
                return refused("no solutions record named " + repr(edit.get("target")))
            answer = self.source.apply({"op": "milestone", "subject": subject, "table": table, "target": target, "key": key, "fields": fields})
            return report(answer, {"table": table, "target": target, "field": "milestones", "after": key})
        table = str(edit.get("table") or "")
        if table not in ADDABLE:
            return refused("no records of the table " + repr(edit.get("table")) + " can be added")
        if not fields:
            return refused("an addition needs the fields of the new record")
        answer = self.source.apply({"op": "add", "subject": subject, "table": table, "target": key, "key": key, "fields": fields})
        return report(answer, {"table": table, "target": str(answer.get("target") or key), "fields": fields})


@implementation("esoi-application", "append_to_description")
class AppendToDescription:
    """Adds the change as a sentence to the end of the record's description: the longer-prompt way, where each correction makes the text longer and no field
    is edited."""
    REQUIRES = ()     # the records are a constructor argument

    def __init__(self, records: Optional[Mapping[str, Mapping[str, Mapping[str, Any]]]] = None):
        self.records = {table: {key: dict(row) for key, row in rows.items()} for table, rows in (records or {}).items()}

    def read(self, subject: str = "") -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        return self.records

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]:
        edit = dict(change.get("edit") or change)
        table = EDITABLE.get(str(edit.get("kind") or ""))
        row = self.records.get(table or "", {}).get(str(edit.get("target") or ""))
        if row is None:
            return refused("no record named " + repr(edit.get("target")))
        row["description"] = str(row.get("description") or "") + " " + str(edit.get("value") or "")
        return {"applied": True, "table": table, "target": str(edit["target"]), "field": "description", "before": "", "after": row["description"]}


def refused(reason: str) -> Dict[str, Any]:
    return {"applied": False, "reason": reason}


def report(answer: Mapping[str, Any], said: Mapping[str, Any]) -> Dict[str, Any]:
    """What the records location answered, as the result of the change: applied (with before and after, or created or already there), proposed (held for a
    person, not done) or refused (plain reason)."""
    status = str(answer.get("status") or "")
    if status == "applied":
        out = {"applied": True, **said}
        if "before" in answer:
            out["before"] = answer["before"]
        if "fields" in said or said.get("field") == "milestones":
            out["created"] = True
        return out
    if status == "unchanged":
        return {"applied": True, **said, "created": False, "note": "already there"}
    if status == "proposed":
        return {"applied": False, "proposed": True, **{k: v for k, v in said.items() if k != "after"}, "decision": answer.get("decision"),
                "reason": "proposed, waiting for approval: " + str(answer.get("reason") or "a person has to say yes before it takes effect")}
    return refused(str(answer.get("reason") or "the records location refused the change"))
