"""cards-from-files: the pinned corpus, the scoring rule, the builders, and the proof that degenerate groupings score nothing.

The corpus tests read Quest AI Runner at its pinned commit through ``git archive`` (a sibling checkout or the folder named by
``CARDS_FROM_FILES_QAR_REPO``); they are skipped, with the reason, on a machine that has no checkout holding that commit."""
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evaluation"))
sys.path.insert(0, str(ROOT))

from cards_from_files import corpus as pinned  # noqa: E402
from cards_from_files import score  # noqa: E402
from hubofhubs.the_intelligence.subconscious.cards_from_files import cards_from_files as arms  # noqa: E402


@pytest.fixture(scope="module")
def corpus():
    try:
        return pinned.load()
    except pinned.PinUnavailable as exc:
        pytest.skip(f"the pinned commits are not available here: {exc}")


def run_all(builder, corpus):
    fn = score.view_function(builder, None)
    return [score.score_case(fn, case) for case in corpus.cases]


def passes(rows):
    return sum(r["raw"] for r in rows)


def test_the_pin_digests_are_filled_and_hold(corpus):
    pin = pinned.read_pin()
    assert len(pin["cases_sha256"]) == 64 and len(pin["files_sha256"]) == 64
    assert len(corpus.cases) == 63 and len(corpus.files) == 892
    assert sum(f.startswith("hubofhubs/") for f in corpus.files) == 149
    assert sum(c["target"].startswith("hubofhubs/") for c in corpus.cases) == 4
    assert all(c["target"] in set(corpus.files) for c in corpus.cases)


def test_a_changed_pin_is_a_hard_error(corpus, monkeypatch):
    pin = pinned.read_pin()
    monkeypatch.setattr(pinned, "_LOADED", {})
    for key in ("cases_sha256", "files_sha256"):
        monkeypatch.setattr(pinned, "read_pin", lambda key=key: dict(pin, **{key: "0" * 64}))
        with pytest.raises(pinned.PinMismatch):
            pinned.load()


def test_the_view_is_read_in_the_builders_own_order(corpus):
    case = corpus.cases[0]
    others = [f for f in corpus.files if f != case["target"]][:3]

    def builder(first):
        return lambda root, files, existing: arms.PerFileSymbols().build(root, files, {}) if first is None else [
            dict(id="one", keywords=[], summary=case["task"], description="", weight=1.0,
                 files=[dict(path=p, symbols=[]) for p in first])]
    behind = score.score_case(score.view_function(builder(others + [case["target"]]), None), case)
    ahead = score.score_case(score.view_function(builder([case["target"]] + others), None), case)
    assert (behind["rank"], behind["raw"]) == (4, False)
    assert (ahead["rank"], ahead["raw"], ahead["top1"]) == (1, True, True)


def test_a_builder_naming_a_file_outside_the_corpus_is_refused(corpus):
    bad = lambda root, files, existing: [dict(id="x", files=[dict(path="no/such.py", symbols=[])])]
    with pytest.raises(ValueError):
        score.score_case(score.view_function(bad, None), corpus.cases[0])


def test_the_floor_reproduces_the_measured_result(corpus):
    rows = run_all(arms.PerFileSymbols().build, corpus)
    assert passes(rows) == 43
    assert sum(r["top1"] for r in rows) == 36 and sum(r["top10"] for r in rows) == 53 and sum(r["anywhere"] for r in rows) == 53
    assert score.aggregate(rows)["cards"] == 892


@pytest.mark.parametrize("name", ["one_card", "two_cards", "one_card_per_folder"])
def test_every_degenerate_builder_scores_zero_where_the_floor_scores_43(corpus, name):
    build = importlib.import_module(f"cards_from_files.broken.{name}").build
    fn = build(None)
    rows = [score.score_case(fn, case) for case in corpus.cases]
    assert passes(rows) == 0 < 43
    assert all(r["anywhere"] or r["view"] for r in rows)   # the needed file is in the view: the loss is the order, not a missing file
    assert max(r["view"] for r in rows) > 500


def test_the_builder_runs_once_and_its_cost_lands_on_the_first_case(corpus):
    calls = []
    def builder(root, files, existing):
        calls.append(1)
        return arms.PerFileSymbols().build(root, files, existing)
    fn = score.view_function(builder, None)
    first, second = score.score_case(fn, corpus.cases[0]), score.score_case(fn, corpus.cases[1])
    assert len(calls) == 2 and "build" in first      # the build, then one refresh from its own cards over the unchanged corpus
    assert "build" in first and "build" not in second
    assert set(first["build"]) == {"cards", "id", "calls", "tokens", "cost", "seconds", "reads", "refresh"}


def test_aggregate_reports_the_details_the_metric_names(corpus):
    rows = [dict(kind="file", raw=True, ok=True, top1=True, top10=True, anywhere=True, penalty=0.0, stored=5, view=10,
                 build=dict(cards=5, id="ab", calls=0, tokens=0, cost=0.0, seconds=1.0,
                            reads=dict(opens=5, files=5, mb=0.1, per_item=1.0), refresh=dict(reads=0, seconds=0.1, share=0.0))),
            dict(kind="file", raw=False, ok=False, top1=False, top10=False, anywhere=True, penalty=0.0, view=30)]
    got = score.aggregate(rows)
    assert (got["file_raw"], got["file_counted"], got["file_top1"], got["file_top10"], got["cards"], got["build"]) == ("1/2", 1, 1, 1, 5, "ab")
    assert got["build_calls"] == 0 and got["store_penalty"] == 0.0


def test_per_file_cards_and_staleness(tmp_path):
    (tmp_path / "a.py").write_text('"""Alpha module."""\n\ndef alpha():\n    pass\n')
    (tmp_path / "b.py").write_text("def beta():\n    pass\n")
    arm = arms.PerFileSymbols()
    cards = arm.build(str(tmp_path), ["a.py", "b.py"], {})
    assert [c["files"][0]["path"] for c in cards] == ["a.py", "b.py"] and "alpha" in cards[0]["files"][0]["symbols"]
    by_id = {c["id"]: c for c in cards}
    assert arm.changed(str(tmp_path), by_id) == []
    (tmp_path / "b.py").write_text("def beta():\n    return 1\n")
    assert arm.changed(str(tmp_path), by_id) == [cards[1]["id"]]
    again = arm.build(str(tmp_path), ["a.py", "b.py"], by_id)
    assert again[0] is not cards[0] and again[0] == cards[0] and again[1]["files"][0]["sha256"] != cards[1]["files"][0]["sha256"]
    (tmp_path / "b.py").unlink()
    assert arm.changed(str(tmp_path), by_id) == [cards[1]["id"]]


class Scripted:
    """A provider that answers the area question, then the topic question, with fixed JSON."""
    def __init__(self):
        self.prompts = []

    def answer(self, messages, model=""):
        self.prompts.append(messages[0]["content"])
        if "identify its top-level areas" in self.prompts[-1]:
            return json.dumps([dict(name="Letters", description="letter modules", files=[1, 2, 3])])
        return json.dumps([dict(id="letters", name="Letters", keywords=["alpha", "beta"], summary="Greek letters", files=[1, 2]),
                           dict(id="letters-again", name="Letters too", keywords=["beta"], summary="Same", files=[1, 2])])


def test_llm_topic_cards_groups_files_and_merges_duplicates(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / f"{name}.py").write_text(f"def {name}_fn():\n    pass\n")
    provider = Scripted()
    cards = arms.LlmTopicCards(provider).build(str(tmp_path), ["a.py", "b.py", "c.py"], {})
    assert len(cards) == 1 and [e["path"] for e in cards[0]["files"]] == ["a.py", "b.py"]
    assert cards[0]["keywords"] == ["alpha", "beta"] and len(provider.prompts) == 2


DATASET = ROOT / "evaluation" / "cards_from_files" / "datasets" / "replays" / "llm_topic_cards_75f9da90.json"


def test_the_persisted_build_loads_with_unique_ids_and_corpus_files(corpus):
    from hubofhubs.the_intelligence.subconscious.cards_from_files import cards_dataset
    document = cards_dataset.load_dataset(DATASET)
    assert document["recorded_build_id"] == "75f9da90" and len(document["cards"]) == 103
    assert document["built"]["model_calls"] == 52
    score.check_cards(document["cards"], corpus.files)   # unique ids and every file in the pinned corpus
    cards_dataset.check_pin(document, pinned.read_pin(), corpus.files)
    assert not any("origin" in card for card in document["cards"]) and "/home/" not in json.dumps(document)


def test_a_changed_dataset_is_refused(tmp_path):
    from hubofhubs.the_intelligence.subconscious.cards_from_files import cards_dataset
    document = json.loads(DATASET.read_text())
    document["cards"][0]["summary"] += " edited"
    path = tmp_path / "edited.json"
    path.write_text(json.dumps(document))
    with pytest.raises(cards_dataset.DatasetError, match="digest"):
        cards_dataset.load_dataset(path)
    document = json.loads(DATASET.read_text())
    document["cards"][1]["id"] = document["cards"][0]["id"]
    document["cards_sha256"] = cards_dataset.cards_digest(document["cards"])
    path.write_text(json.dumps(document))
    with pytest.raises(cards_dataset.DatasetError, match="same id"):
        cards_dataset.load_dataset(path)


def test_a_replay_on_another_pin_or_corpus_is_refused():
    from hubofhubs.the_intelligence.subconscious.cards_from_files import cards_dataset
    pin = pinned.read_pin()
    with pytest.raises(cards_dataset.DatasetError, match="another corpus"):
        arms.TopicCardsReplay(pin=dict(pin, qar_commit="deadbeef"))
    with pytest.raises(cards_dataset.DatasetError, match="another corpus"):
        arms.FilePlusTopicCards(pin=dict(pin, cases_sha256="0" * 64))
    with pytest.raises(cards_dataset.DatasetError, match="files differ"):
        arms.TopicCardsReplay(pin=pin).build("", ["a.py"], {})


@pytest.mark.parametrize("arm", [arms.TopicCardsReplay, arms.FilePlusTopicCards])
def test_the_replay_arms_are_built_without_a_model(arm):
    import inspect
    assert arm.REQUIRES == () and "provider" not in inspect.signature(arm).parameters
    assert score.needs(arm, None) == dict(pin=pinned.read_pin())


def test_the_replay_and_the_combination_reproduce_the_measured_results(corpus):
    replay = run_all(arms.TopicCardsReplay(pin=pinned.read_pin()).build, corpus)
    both = run_all(arms.FilePlusTopicCards(pin=pinned.read_pin()).build, corpus)
    assert passes(replay) == 5 and passes(both) == 40
    assert sum(r["top1"] for r in both) == 35 and sum(r["top10"] for r in both) == 47 and sum(r["anywhere"] for r in both) == 50
    cards = arms.FilePlusTopicCards(pin=pinned.read_pin()).build(str(corpus.root), corpus.files, {})
    assert len(cards) == 892 + 103 and sum(c["id"].startswith("topic-") for c in cards) == 103


def test_a_replay_is_reported_beside_the_build_never_as_its_cost(corpus):
    fn = score.adapt(arms.TopicCardsReplay, None)
    first = score.score_case(fn, corpus.cases[0])
    assert first["build"]["cost"] == 0.0 and first["build"]["replayed"]["calls"] == 52
    assert "from build 75f9da90" in score.aggregate([first])["replayed"]
