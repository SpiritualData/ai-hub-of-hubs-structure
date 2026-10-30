"""Offline tests of the scorer against a small fake consumer: no model call, no network."""
import csv
from datetime import date
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import Binding, cases, evaluate, registry, render_docs, scan  # noqa: E402
from hubofhubs.measure import KINDS, check  # noqa: E402


def write(path, header, rows):
    with open(path, "w", newline="") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def consumer(tmp_path):
    """A fake consumer: one core file with a vendor branch, records for one seam solution, a probe that passes."""
    core = tmp_path / "core"
    core.mkdir()
    (core / "route.py").write_text('def f(m):\n    if m.startswith("acmevendor"):\n        return 1\n    return {"acmevendor": 2}.get(m)\n')
    rec = tmp_path / "esoi"
    rec.mkdir()
    write(rec / "solutions.csv", ["solution_id", "authoritative_metric_id"], [["seam-a", "metric-a"]])
    write(rec / "implementations.csv", ["implementation_id", "solution_id"], [["seam-a:x", "seam-a"], ["seam-a:y", "seam-a"]])
    seats = [{"area": a, "seam_solution_id": "seam-a" if a == "model_providers" else "", "vendor_terms": "acmevendor" if a == "model_providers" else "",
              "code_paths": ""} for a in (r["area"] for r in registry.read("hubs.csv"))]
    return Binding(consumer="quest-ai-runner", root=tmp_path, seats=seats, core_dir=core, records_dir=rec,
                   names_of=lambda sid: ["x", "y"] if sid == "seam-a" else [], probes={"model_providers": lambda: (True, "ok")})


def test_a_consumer_is_read_per_area(consumer):
    facts, connections, numbers = evaluate(consumer)
    mp = facts["model_providers"]
    assert mp["seam"] and mp["selectable"] and mp["vendor_branches"] and check(mp, "fake_hub")["holds"]
    assert not check(mp, "core_clean")["holds"]
    assert not check(facts["voice"], "fake_hub")["holds"]                    # no probe: unproven, not assumed
    assert all(c["consumer"] == "quest-ai-runner" and c["wired"] == "yes" for c in connections)
    assert 0 <= numbers["score"] <= 1


def test_every_area_gets_every_check():
    got = {(c["args"]["area"], c["kind"]) for c in cases.cases()}
    assert got == {(r["area"], k) for r in registry.read("hubs.csv") for k in KINDS}


def test_freshness_ages_with_the_calendar(consumer):
    facts, _, _ = evaluate(consumer)
    assert all(f["fresh"] for f in facts.values())
    facts, _, numbers = evaluate(consumer, today=date(2099, 1, 1))
    assert not any(f["fresh"] for f in facts.values()) and numbers["fresh_share"] == 0 and numbers["days_mean"] > 90


def test_arithmetic_on_a_planted_registry():
    facts = [dict(registered=True, fresh=True, seam=True, selectable=True, vendor_branches=[], days=10),
             dict(registered=False, fresh=False, seam=False, selectable=False, vendor_branches=["x"], days=110)]
    conns = [dict(connect="config"), dict(connect="code"), dict(connect="code"), dict(connect="code")]
    m = registry.combine(facts, conns)
    assert (m["coverage"], m["config_share"], m["fresh_share"], m["days_max"], m["days_mean"]) == (0.5, 0.25, 0.5, 110, 60)
    assert m["score"] == pytest.approx((0.5 + 0.25 + 0.5 + 0.5 + 1.0) / 5)


def test_scan_counts_branches_not_tables(tmp_path):
    (tmp_path / "a.py").write_text('def f(m):\n    if m.startswith("gemini"):\n        return 1\n')
    (tmp_path / "b.py").write_text('T = {"gemini": 1}\nx = T.get("gemini")\n"""gemini"""\n')
    found = scan.scan_core({"m": ["gemini"], "n": ["gem"]}, tmp_path, tmp_path)
    assert len(found["m"]) == 1 and "a.py:2" in found["m"][0] and found["n"] == []


def test_a_prepared_connection_and_a_waived_integration_do_not_count():
    conns = [dict(consumer="c", area="a", connect="config", wired="no"), dict(consumer="c", area="a", connect="code", wired="yes"),
             dict(consumer="d", area="a", connect="code", wired="yes")]
    assert len(registry.connections_of("a", conns, "c")) == 1
    ints = [dict(consumer="c", area="a", integration="x", covered_by="Hub", status="violation"),
            dict(consumer="c", area="a", integration="y", covered_by="Hub", status="waived"),
            dict(consumer="c", area="a", integration="z", covered_by="", status="violation")]
    assert [i["integration"] for i in registry.reinvented_of("a", ints, "c")] == ["x"]


# A sub-solution area may weigh many candidates (the widest, prompt-injection defence, carries 16), because Joshua asked for broad
# seats to be broken into sub-solutions and metrics, so the cap is 16, not the 4 of the first-pass research. An area that would
# need more is split into narrower areas. The checks that matter stay strict: at least 2 candidates unless the area names a
# single one, every finding has an https url and evidence url, a licence, a parseable date and a source quality, a role from the
# known vocabulary, ids are unique, and hubs.csv joins to findings by id prefix with no orphan on either side.
MOST_FINDINGS = 16
ROLES = {"adopt", "avoid", "builds_on", "coexist", "compare", "incorporate", "watch"}


def test_registry_integrity():
    hubs = registry.read("hubs.csv")
    findings = registry.read("hub_findings.csv")
    areas = [r["area"] for r in hubs]
    assert len(set(areas)) == len(areas)
    assert len({r["finding_id"] for r in hubs}) == len(hubs)
    ids = [f["finding_id"] for f in findings]
    assert len(set(ids)) == len(ids), "finding ids must be unique, one per row"
    joined = []
    for row in hubs:
        mine = registry.findings_of(row, findings)
        joined += mine
        single = len(registry.split(row["candidate_hubs"])) <= 1
        assert (1 if single else 2) <= len(mine) <= MOST_FINDINGS, (row["area"], len(mine))
        assert all(f["area"] == row["area"] for f in mine), row["area"]
        assert [f["finding_id"] for f in mine] == [f"{row['finding_id']}-{n}" for n in range(1, len(mine) + 1)], row["area"]
        assert registry.days_since(row["last_researched"]) is not None
    assert len(joined) == len(findings), "every finding belongs to an area of hubs.csv"
    for f in findings:
        assert f["url"].startswith("https://") and f["evidence_url"].startswith("https://"), f["finding_id"]
        assert f["license"].strip() and f["source_quality"].strip() and f["summary"].strip(), f["finding_id"]
        assert f["role"] in ROLES, f["finding_id"]
        assert registry.days_since(f["date_researched"]) is not None, f["finding_id"]
    for cap in registry.read("hub_capabilities.csv"):
        assert cap["connect"] in ("config", "code") and cap["wired"] in ("yes", "no")
        assert cap["area"] in areas, cap["capability_id"]
        named = ("serper", "brave", "tavily", "notion", "drive", "chat", "anthropic", "gemini", "deepseek")
        assert not any(n in cap["capability"].lower() for n in named), cap["capability_id"]
    for item in registry.read("hub_integrations.csv"):
        assert item["area"] in areas, item["integration"]
        assert item["status"] in ("violation", "waived")
        assert item["status"] == "violation" or item["waiver_reason"].strip()


def test_findings_join_by_prefix_without_crossing_areas():
    hubs = [dict(area="science", finding_id="HF-1-science"), dict(area="science_graph", finding_id="HF-1-science_graph")]
    findings = [dict(finding_id="HF-1-science-1"), dict(finding_id="HF-1-science_graph-1"), dict(finding_id="HF-1-science_graph-2")]
    assert [f["finding_id"] for f in registry.findings_of(hubs[0], findings)] == ["HF-1-science-1"]
    assert len(registry.findings_of(hubs[1], findings)) == 2


def test_the_example_lane_is_one_aggregator_with_no_secret():
    text = (Path(registry.DATA).parent / "examples" / "lane-world-hub.toml").read_text()
    assert text.count("[[mcp_servers]]") == 1 and "token_env" in text and "Bearer" not in text


def test_rewrite_swaps_a_block_in_place():
    out = render_docs.rewrite("a\n<!-- b -->\nold\n<!-- e -->\nz", "<!-- b -->", "<!-- e -->", "new")
    assert out == "a\n<!-- b -->\nnew\n<!-- e -->\nz"
