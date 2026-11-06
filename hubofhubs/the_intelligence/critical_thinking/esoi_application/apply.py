"""ESOI Application: applies one proposed change to the specs and metrics it is handed, as an edit to a record field and never as a longer prompt,
and says exactly what changed. Standard library plus ``esoi``."""
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

EDITABLE = {"spec_edit": "solutions", "metric_edit": "metrics", "quality_profile_edit": "profiles"}
EM_DASH = "—"


@implementation("esoi-application", "record_field_edit")
class RecordFieldEdit:
    """Sets the one field a change names on the one record it names, in the table its kind belongs to (specs, metrics, quality profiles). It refuses a change
    whose target or field does not exist, whose kind is unknown or whose new value is empty or carries an em dash, and says why; a refused change leaves
    every record as it was."""
    REQUIRES = ()     # the records are a constructor argument

    def __init__(self, records: Optional[Mapping[str, Mapping[str, Mapping[str, Any]]]] = None):
        self.records = {table: {key: dict(row) for key, row in rows.items()} for table, rows in (records or {}).items()}

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]:
        edit = dict(change.get("edit") or change)
        table = EDITABLE.get(str(edit.get("kind") or ""))
        if table is None:
            return refused("the change kind " + repr(edit.get("kind")) + " is not an edit to a spec, a metric or a quality profile")
        row = self.records.get(table, {}).get(str(edit.get("target") or ""))
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
        before = row[field]
        row[field] = value
        return {"applied": True, "table": table, "target": str(edit["target"]), "field": field, "before": before, "after": value}


@implementation("esoi-application", "append_to_description")
class AppendToDescription:
    """Adds the change as a sentence to the end of the record's description: the longer-prompt way, where each correction makes the text longer and no field
    is edited."""
    REQUIRES = ()     # the records are a constructor argument

    def __init__(self, records: Optional[Mapping[str, Mapping[str, Mapping[str, Any]]]] = None):
        self.records = {table: {key: dict(row) for key, row in rows.items()} for table, rows in (records or {}).items()}

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
