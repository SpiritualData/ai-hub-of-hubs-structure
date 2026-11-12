"""record_investigation writes an investigation without editing the CSV files: defaults, checks against the standard, the JSON file form and the command."""
import csv
import json

import pytest

from hubofhubs.the_self.assembler.cli import main
from hubofhubs.the_world.learning import investigation_store as store

ROW = {"question": "Which parser library is current?", "decision": "adopt one parser", "intent_id": "x", "size": "quick", "method": "read the pages", "criteria": "Included: maintained",
       "sources": "opened pages", "queries": "opened | https://example.org/a | 2026-11-11 | 1", "found": "2", "screened_out": "1 not maintained", "kept": "1",
       "limitations": "one page read", "decisions": "alpha: adopt: maintained", "links": "solution:the-learning", "done_on": "2026-11-11"}
ITEM = {"claim": "alpha is maintained", "source": "https://example.org/a", "independent": "yes", "verified": "opened", "grade": "B", "applied": "none"}


def rows(folder, name):
    with open(folder / name, newline="") as handle:
        return list(csv.DictReader(handle))


def test_defaults_are_filled_and_both_files_written(tmp_path):
    done = store.record_investigation({"investigation": ROW, "items": [ITEM]}, tmp_path)
    assert done["gaps"] == [] and done["investigation_id"] == "inv-2026-11-11-which-parser-library-is-current"
    row, = rows(tmp_path, "investigations.csv")
    assert row["status"] == "open" and row["kind"] == "review" and row["protocol_date"] == "2026-11-11" and row["refresh_on"] == "2026-12-11"
    item, = rows(tmp_path, "investigation_items.csv")
    assert item["item_id"] == "i1" and item["investigation_id"] == row["investigation_id"]


def test_a_record_with_gaps_is_refused_and_nothing_is_written(tmp_path):
    thin = dict(ROW, limitations="")
    with pytest.raises(ValueError, match="has no limitations"):
        store.record_investigation({"investigation": thin, "items": [ITEM]}, tmp_path)
    with pytest.raises(ValueError, match="names no source"):
        store.record_investigation({"investigation": ROW, "items": [dict(ITEM, source="")]}, tmp_path)
    assert not (tmp_path / "investigations.csv").exists()


def test_rewriting_the_same_id_replaces_and_links_fall_back_to_the_top_solution(tmp_path):
    bare = {k: v for k, v in ROW.items() if k != "links"}
    store.record_investigation({"investigation": bare, "items": [ITEM]}, tmp_path)
    store.record_investigation({"investigation": dict(bare, decisions="alpha: reject: stale"), "items": [ITEM]}, tmp_path)
    row, = rows(tmp_path, "investigations.csv")
    assert row["links"] == "solution:" + store.TOP_SOLUTION and "reject" in row["decisions"]
    assert len(rows(tmp_path, "investigation_items.csv")) == 1


def test_the_command_reads_a_json_file(tmp_path, capsys):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({"investigation": ROW, "items": [ITEM]}), encoding="utf-8")
    assert main(["investigation", "record", str(path), "--folder", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "inv-2026-11-11-which-parser-library-is-current"
    path.write_text(json.dumps({"investigation": dict(ROW, decisions=""), "items": [ITEM]}), encoding="utf-8")
    assert main(["investigation", "record", str(path), "--folder", str(tmp_path)]) == 1
