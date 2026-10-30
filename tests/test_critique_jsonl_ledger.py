"""The keyed JSON-lines ledger: one file per key, appends that never raise, and a folder an account can always write."""
import os

from hubofhubs.critique import jsonl_ledger


def test_an_account_that_cannot_write_the_shared_folder_gets_its_own(tmp_path, monkeypatch):
    """The shared default folder belongs to the account that made it; another account's runs must still record."""
    shared = tmp_path / "ledger"
    shared.mkdir()
    monkeypatch.setattr(jsonl_ledger.tempfile, "gettempdir", lambda: str(tmp_path))
    assert jsonl_ledger.default_directory("ledger") == str(shared)
    real_access = os.access
    monkeypatch.setattr(os, "access", lambda p, m: False if str(p) == str(shared) else real_access(p, m))
    assert jsonl_ledger.default_directory("ledger") == f"{shared}-{os.getuid()}"


def test_the_tool_ledger_keeps_its_files_with_esois_run_files(tmp_path):
    """The file-per-key store is esoi's: one implementation, not a copy beside it."""
    from esoi.metric_results import RunFiles
    from hubofhubs.act.tool_ledger import FileToolLedger
    ledger = FileToolLedger(str(tmp_path))
    assert type(ledger.files) is RunFiles and not hasattr(jsonl_ledger, "KeyedJsonlFiles")
    assert os.path.dirname(ledger.path_for("../../etc/passwd")) == str(tmp_path)
