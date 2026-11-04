"""The committed case sources of context_retrieval: pins, counts against the shares fixed in mix.py, labels. No model, no network."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation"))

from context_retrieval import memory, mix, open_code

HERE = Path(__file__).resolve().parent.parent / "evaluation" / "context_retrieval"


def test_the_pools_hold_exactly_the_counts_the_shares_give():
    unit = 63
    assert round(unit * mix.MIX["memory"]) == len(memory.cases()) == 47
    cases = open_code.cases()
    assert round(unit * mix.MIX["topic_open"]) == len(cases["topic_open"]) == 63
    assert round(unit * mix.MIX["grouping"]) == len(cases["grouping"]) == 32
    assert all(len(pool) >= mix.MIN_CASES[kind] for kind, pool in (("memory", memory.cases()), *cases.items()))


def test_the_memory_sample_is_pinned_and_carries_the_licence_notice():
    memory._SAMPLE.clear()
    assert memory.sample()["cases"]                                    # the sha256 of the sample is checked here
    pin = json.loads((HERE / "datasets/memory/pin.json").read_text())
    assert pin["licence"] == "MIT" and len(pin["upstream_sha256"]) == 64
    assert "MIT License" in (HERE / "datasets/memory/LICENSE-LongMemEval.txt").read_text()


def test_a_superseded_fact_is_irrelevant_and_an_unanswered_question_needs_nothing():
    for c in memory.cases():
        if c["abstention"]:
            assert c["needed"] == [] and c["helpful"] == []
        else:
            assert c["needed"], c["id"]
    update = next(c for c in memory.cases() if c["question_type"] == "knowledge-update")
    older = [sid for sid, stamp in update["haystack"] if sid in update["evidence_sessions"] and stamp < max(dict(update["haystack"])[s] for s in update["evidence_sessions"])]
    assert older and not any(f"/{sid}/" in p for sid in older for p in update["needed"] + update["helpful"])


def test_memory_items_carry_time_and_role_from_the_benchmark():
    case = memory.cases()[0]
    files, meta = memory.world_of(case)
    assert set(files) == set(meta)
    assert {m["author_role"] for m in meta.values()} <= {"requester", "assistant"} and all(m["timestamp"].startswith("20") for m in meta.values())


def test_open_cases_are_newer_than_the_history_and_grouping_asks_from_the_sibling():
    pin = json.loads((HERE / "datasets/open_code/pin.json").read_text())
    cases = open_code.cases()
    every = cases["topic_open"] + cases["grouping"]
    assert min(c["date"] for c in every) >= pin["oldest_case_date"]
    history = open_code.checked(open_code.HISTORY_FILE, "history_sha256", "commits")
    assert history and max(c["date"] for c in history) < pin["oldest_case_date"]
    assert all(c["focus"] == [open_code.tag(c["repo"])] for c in cases["topic_open"])
    assert all(c["focus"] == [open_code.tag(open_code.SIBLING[c["repo"]])] for c in cases["grouping"])
    assert all(p.startswith(c["repo"] + "/") for c in every for p in c["needed"])
    assert {r["licence"] for r in pin["repos"].values()} == {"BSD-3-Clause"}


def test_the_new_files_never_say_the_consumer_word():
    import re
    word = re.compile(r"(?<![A-Za-z])quest(?![a-z])", re.I)
    names = ["memory.py", "open_code.py", "mix.py", "score.py", "gate.py"] + [f"impls/{n}.py" for n in ("abstaining_recency", "abstaining_affinity", "abstaining_aware", "abstaining_fenced", "live_scan")]
    hits = [n for n in names if (HERE / n).exists() and word.search((HERE / n).read_text())]
    assert hits == []
