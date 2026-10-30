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


def test_appends_are_read_back_in_order_and_a_torn_line_is_skipped(tmp_path):
    files = jsonl_ledger.KeyedJsonlFiles(str(tmp_path))
    assert files.append("run-1", {"a": 1}) and files.append("run-1", {"b": 2})
    with open(files.path_for("run-1"), "a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    assert files.read("run-1") == [{"a": 1}, {"b": 2}]
    assert files.read("unknown") == [] and files.append("", {"a": 1}) is False


def test_a_key_cannot_leave_the_directory(tmp_path):
    files = jsonl_ledger.KeyedJsonlFiles(str(tmp_path))
    assert os.path.dirname(files.path_for("../../etc/passwd")) == str(tmp_path)
