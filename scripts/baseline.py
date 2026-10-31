"""Record the executed-line share of the hub's own code, per implementation id.

Dev-only (needs `coverage`). Runs the scoped tests, then maps each module to the implementation
whose `filepath` it is; modules no record names are grouped under "unassigned". Writes
docs/reference/baseline.json. `--check` compares against the stored file and fails on a drop beyond the
tolerance. The key is the implementation id, so a module move does not break the baseline.
"""
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "reference" / "baseline.json"
TESTS = ["tests/test_registry.py", "tests/test_status.py", "tests/test_tiers.py", "tests/test_no_environment.py",
         "tests/test_resolution.py", "tests/test_safe_loading.py", "tests/test_example_consumer.py",
         "tests/test_graph.py", "tests/test_cardstore.py", "tests/test_quickstart.py", "tests/test_metadata.py",
         "tests/test_recall_background_pacing.py", "tests/test_recall_card_content.py", "tests/test_recall_card_store_lock.py",
         "tests/test_recall_card_thread.py", "tests/test_recall_composite_assembler.py", "tests/test_recall_conversation_format.py",
         "tests/test_recall_text_sampling.py", "tests/test_recall_walk.py",
         "tests/test_recall_bootstrap_support.py", "tests/test_recall_card_ceilings.py", "tests/test_recall_card_limit.py", "tests/test_recall_card_limit_report.py", "tests/test_recall_card_origin.py", "tests/test_recall_card_repository.py", "tests/test_recall_card_store_identity.py", "tests/test_recall_card_store_merge.py", "tests/test_recall_card_store_mounts.py", "tests/test_recall_card_store_tidy.py", "tests/test_recall_folder_review.py", "tests/test_recall_index_file_refs.py", "tests/test_recall_scope_tags.py",
         "tests/test_critique_jsonl_ledger.py", "tests/test_critique_link_detect.py", "tests/test_critique_link_guard.py",
         "tests/test_critique_specificity.py", "tests/test_critique_sufficiency.py",
         "tests/test_ports_deep.py", "tests/test_act_execution_record.py", "tests/test_act_editblock.py", "tests/test_act_mcp_client.py", "tests/test_act_tool_ledger.py",
         "tests/test_act_fast_edit.py", "tests/test_act_mcp_operations.py"]
TOLERANCE = 1.0  # percentage points


def measure() -> dict:
    import coverage

    with tempfile.TemporaryDirectory() as tmp:
        data = str(Path(tmp) / "cov")
        env = {"COVERAGE_FILE": data, "PATH": "/usr/bin:/bin"}
        subprocess.run(
            [sys.executable, "-m", "coverage", "run", "--source=hubofhubs", "-m", "pytest", "-q", *TESTS],
            cwd=ROOT, check=True, env={**env, "PYTHONPATH": str(ROOT)},
            stdout=subprocess.DEVNULL,
        )
        cov = coverage.Coverage(data_file=data)
        cov.load()
        owner = {}
        with open(ROOT / "esoi" / "implementations.csv", newline="") as handle:
            for row in csv.DictReader(handle):
                owner[(ROOT / row["filepath"]).resolve()] = row["implementation_id"]
        totals: dict = {}
        for name in cov.get_data().measured_files():
            path = Path(name).resolve()
            if ROOT not in path.parents:
                continue
            _, statements, _, missing, _ = cov.analysis2(name)
            key = owner.get(path, "unassigned")
            entry = totals.setdefault(key, [0, 0])
            entry[0] += len(statements) - len(missing)
            entry[1] += len(statements)
    return {
        key: {"executed": hit, "statements": total, "percent": round(100 * hit / total, 1) if total else 100.0}
        for key, (hit, total) in sorted(totals.items())
    }


def main() -> int:
    now = measure()
    if "--check" in sys.argv:
        stored = json.loads(OUT.read_text())
        bad = [k for k, v in stored.items() if now.get(k, {"percent": 0})["percent"] < v["percent"] - TOLERANCE]
        for key in bad:
            print(f"baseline dropped: {key} {stored[key]['percent']} -> {now.get(key, {}).get('percent', 0)}")
        return 1 if bad else 0
    OUT.write_text(json.dumps(now, indent=1) + "\n")
    print(json.dumps(now, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
