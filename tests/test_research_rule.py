"""Rule L1 (scripts/esoi_rules.py): a finding researched on or after `since` names an investigation that exists, a kept item has a source, and the rule is advisory until `fail_from`."""
import csv
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from hubofhubs.the_world.learning import investigation_record as inv

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "esoi_rules.py"


def load():
    spec = importlib.util.spec_from_file_location("hub_esoi_rules", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def repo(tmp_path, findings, items=()):
    folder = tmp_path / "hubofhubs" / "registry"
    write(folder / "hub_findings.csv", ["finding_id", "area", "date_researched", "investigation_id"], findings)
    write(folder / "investigations.csv", inv.COLUMNS, [{"investigation_id": "inv-1", "links": "solution:a"}])
    write(folder / "investigation_items.csv", inv.ITEM_COLUMNS, items)
    return tmp_path


def ctx(root, options, waived=()):
    config = SimpleNamespace(option=lambda rule, key, default=None: options.get(key, default))
    return SimpleNamespace(root=root, config=config, advisory=[], waived=lambda rule, key: key in waived)


def test_findings_before_since_are_not_asked_and_later_ones_must_name_an_existing_investigation(tmp_path):
    root = repo(tmp_path, [{"finding_id": "F1", "area": "x", "date_researched": "2026-11-01", "investigation_id": ""},
                           {"finding_id": "F2", "area": "x", "date_researched": "2026-11-12", "investigation_id": ""},
                           {"finding_id": "F3", "area": "x", "date_researched": "2026-11-12", "investigation_id": "inv-9"},
                           {"finding_id": "F4", "area": "x", "date_researched": "2026-11-12", "investigation_id": "inv-1"}])
    found = load().problems(ctx(root, {"since": "2026-11-11"}))
    assert [line.split(":")[0] for line in found] == ["L1 F2", "L1 F3"]
    assert load().problems(ctx(root, {"since": "2026-11-11"}, waived=("F2", "F3"))) == []


def test_a_kept_item_needs_a_source(tmp_path):
    root = repo(tmp_path, [], [{"investigation_id": "inv-1", "item_id": "i1", "source": ""}])
    assert load().problems(ctx(root, {"since": "2026-11-11"})) == ["L1 inv-1:i1: a kept item has no source"]


def test_advisory_before_fail_from_and_failing_after(tmp_path):
    root = repo(tmp_path, [{"finding_id": "F2", "area": "x", "date_researched": "2026-11-12", "investigation_id": ""}])
    soon = ctx(root, {"since": "2026-11-11", "fail_from": "9999-01-01"})
    assert load().research_recorded(soon) == [] and len(soon.advisory) == 1
    due = ctx(root, {"since": "2026-11-11", "fail_from": "2000-01-01"})
    assert len(load().research_recorded(due)) == 1 and due.advisory == []
