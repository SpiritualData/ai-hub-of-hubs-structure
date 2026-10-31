"""Offline tests of the scorer against a small fake consumer: no model call, no network."""
import csv
from datetime import date
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import Binding, cases, evaluate, evaluate_seats, registry, render_docs, scan  # noqa: E402
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


def test_a_consumer_is_read_per_area_and_per_seat(consumer):
    facts, connections, numbers = evaluate(consumer)
    mp = facts["model_providers"]
    assert mp["seam"] and mp["selectable"] and mp["vendor_branches"] and check(mp, "fake_hub")["holds"]
    assert not check(mp, "core_clean")["holds"]
    assert not check(facts["voice"], "fake_hub")["holds"]                    # no probe: unproven, not assumed
    assert all(c["consumer"] == "quest-ai-runner" and c["wired"] == "yes" for c in connections)
    assert 0 <= numbers["score"] <= 1


def test_every_area_and_every_seat_gets_the_checks_that_apply_to_it():
    got = {(c["args"].get("area") or c["args"]["seat"], c["kind"]) for c in cases.cases()}
    hubs = registry.read("hubs.csv")
    want = {(r["area"], k) for r in hubs for k in registry.AREA_KINDS}
    want |= {(s, k) for s in registry.seat_ids(hubs) for k in registry.SEAT_KINDS
             if k not in registry.CONNECTION_KINDS or registry.seat_should_connect(hubs, s)}
    assert got == want
    assert set(KINDS) == set(registry.AREA_KINDS) | set(registry.SEAT_KINDS), "every kind is checked either per area or per seat"


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


# THE CALL COLUMN. `call` is the recommendation as one machine-readable word, so a scorer can tell an area a consumer should be connected
# to (adopt, coexist) from one it should not (keep, watch, avoid) without parsing prose. A blank is read as coexist.
def test_every_area_has_a_known_call_that_its_recommendation_states():
    for row in registry.read("hubs.csv"):
        assert row["call"] in registry.CALLS, (row["area"], row["call"])      # a blank would count as coexist; none is blank today
        words = row["recommendation"].upper().split()
        if words[0].strip(".,;:") in ("ADOPT", "WATCH", "AVOID"):
            assert row["call"] == words[0].strip(".,;:").lower(), row["area"]


def test_only_adopt_coexist_and_blank_should_be_connected():
    for call, wanted in (("adopt", True), ("coexist", True), ("", True), ("keep", False), ("watch", False), ("avoid", False)):
        assert registry.should_connect({"call": call}) is wanted, call
    assert registry.should_connect({}) is True, "a row with no call column is unclassified, so it counts as coexist"
    assert registry.should_connect({"call": " Keep "}) is False


def test_seam_and_selectable_shares_are_over_the_areas_that_should_be_connected():
    base = dict(registered=True, fresh=True, vendor_branches=[], days=1)
    facts = [dict(base, area="a", expected=True, seam=True, selectable=True), dict(base, area="b", expected=True, seam=False, selectable=False),
             dict(base, area="c", expected=False, seam=False, selectable=False), dict(base, area="d", expected=False, seam=False, selectable=False)]
    m = registry.combine(facts, [])
    assert (m["seam_share"], m["selectable_share"], m["to_connect"], m["unconnected"]) == (0.5, 0.5, 2, ["b"])
    assert m["code"] == pytest.approx((0.5 + 0.5 + 1.0) / 3), "the weights of the terms are unchanged"
    none_wanted = registry.combine([dict(base, area="c", expected=False, seam=False, selectable=False)], [])
    assert none_wanted["seam_share"] == 1.0 and none_wanted["to_connect"] == 0


def test_connection_checks_are_cases_only_for_seats_with_an_area_that_should_be_connected():
    from hubofhubs import cases
    hubs = registry.read("hubs.csv")
    have = {(c["args"]["seat"], c["kind"]) for c in cases.cases() if "seat" in c["args"]}
    for seat in registry.seat_ids(hubs):
        for kind in registry.SEAT_KINDS:
            expected = kind not in registry.CONNECTION_KINDS or registry.seat_should_connect(hubs, seat)
            assert ((seat, kind) in have) is expected, (seat, kind)
    assert not {c["args"]["area"] for c in cases.cases() if "area" in c["args"] and c["kind"] in registry.CONNECTION_KINDS}, \
        "no connection check is made per area"


def test_every_area_maps_to_a_seat_of_the_mind():
    from esoi.tables import read_csv
    root = Path(__file__).resolve().parent.parent
    solutions = {r["solution_id"] for r in read_csv(root / "esoi" / "solutions.csv")}
    hubs = registry.read("hubs.csv")
    assert all(r["seat"] in solutions for r in hubs), [r["area"] for r in hubs if r["seat"] not in solutions]
    assert len(registry.seat_ids(hubs)) <= 12


def test_one_row_per_seat_binds_every_area_that_seat_owns_and_the_rest_are_arm_gaps(tmp_path, consumer):
    hubs = registry.read("hubs.csv")
    by_seat = {}
    for r in hubs:
        by_seat.setdefault(r["seat"], []).append(r["area"])
    one_row = [dict(seat="reason-and-answer", areas="model_providers", seam_solution_id="seam-a", vendor_terms="acmevendor", code_paths="")]
    seat_consumer = Binding(consumer="quest-ai-runner", root=consumer.root, seats=one_row, core_dir=consumer.core_dir,
                            records_dir=consumer.records_dir, names_of=consumer.names_of, probes={"model_providers": lambda: (True, "ok")})
    facts, seat_facts, _, numbers = evaluate_seats(seat_consumer)
    mine = seat_facts["reason-and-answer"]
    assert mine["seam"] and mine["selectable"] and mine["probe"] is not None and mine["vendor_branches"]
    assert mine["covered"] == ["model_providers"] and "structured_output" in mine["arm_gaps"], "an uncovered adopt area is an arm gap"
    assert not seat_facts["know-the-world"]["seam"] and not seat_facts["know-the-world"]["bound"]
    assert "reason-and-answer" not in numbers["unconnected_seats"] and "know-the-world" in numbers["unconnected_seats"]
    assert facts["structured_output"]["seam"] is False and facts["model_providers"]["seam"] is True, "per-area data stays in the facts"
    assert numbers["seam_share"] == pytest.approx(1 / numbers["seats_to_connect"])
    assert {a for a in numbers["arm_gaps"]} == {a for a, f in facts.items() if f["expected"] and not f["covered"]}


def test_a_row_that_puts_an_area_under_the_wrong_seat_is_refused(consumer):
    bad = Binding(consumer="quest-ai-runner", root=consumer.root, seats=[dict(seat="know-the-world", areas="model_providers")],
                  core_dir=consumer.core_dir, records_dir=consumer.records_dir, names_of=consumer.names_of)
    with pytest.raises(ValueError, match="belongs to seat"):
        evaluate(bad)


def test_a_seat_with_no_probe_is_unproven_and_probes_of_its_arms_must_all_hold(consumer):
    mixed = Binding(consumer="quest-ai-runner", root=consumer.root, core_dir=consumer.core_dir, records_dir=consumer.records_dir,
                    names_of=consumer.names_of, seats=[dict(seat="take-in-the-world", areas="channels;integration_aggregators")],
                    probes={"channels": lambda: (True, "a"), "integration_aggregators": lambda: (False, "b")})
    _, seat_facts, _, _ = evaluate_seats(mixed)
    assert not check(seat_facts["take-in-the-world"], "fake_hub")["holds"]
    assert not check(seat_facts["act-in-the-world"], "fake_hub")["holds"]
