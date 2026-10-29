"""The hub's default card store: the first executing implementation."""
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import HubConfig, assemble, resolve  # noqa: E402
from hubofhubs.card import Card  # noqa: E402
from hubofhubs.cardstore import LocalCardStore  # noqa: E402
from hubofhubs.seats import CardStore  # noqa: E402


@pytest.fixture
def store():
    made = LocalCardStore()
    yield made
    made.close()


def test_it_satisfies_the_seat(store):
    assert isinstance(store, CardStore)


def test_add_get_and_replace_by_id(store):
    assert store.add(Card("a", "first text", source="s", tags=("x", "y"))) == "a"
    assert store.get("a") == Card("a", "first text", "s", ("x", "y"))
    store.add(Card("a", "second text"))
    assert store.get("a") == Card("a", "second text") and store.count() == 1
    assert store.get("missing") is None


def test_search_matches_every_word_any_case_and_a_tag(store):
    store.add(Card("1", "The quick brown fox", tags=("animal",)))
    store.add(Card("2", "A quick red car", tags=("vehicle",)))
    store.add(Card("3", "Slow brown bear", tags=("animal",)))
    assert [c.id for c in store.search("QUICK")] == ["1", "2"]
    assert [c.id for c in store.search("quick brown")] == ["1"]
    assert [c.id for c in store.search("brown", tag="animal")] == ["1", "3"]
    assert [c.id for c in store.search("", limit=2)] == ["1", "2"]
    assert store.search("nothing here") == [] and store.search("quick", limit=0) == []


def test_delete(store):
    store.add(Card("a", "x"))
    assert store.delete("a") is True and store.delete("a") is False and store.count() == 0


def test_a_file_store_survives_a_second_instance(tmp_path):
    path = str(tmp_path / "cards.db")
    first = LocalCardStore(path)
    first.add(Card("a", "kept"))
    first.close()
    second = LocalCardStore(path)
    assert second.get("a").text == "kept"
    second.close()


def test_threads_can_add_at_once(store):
    threads = [threading.Thread(target=store.add, args=(Card(str(i), "t"),)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert store.count() == 20


def test_it_is_the_hub_default_and_takes_its_path_from_the_config(tmp_path):
    assert resolve("card-store") is LocalCardStore
    path = tmp_path / "cards.db"
    system = assemble(HubConfig(seats=("card-store",), options={"card-store": {"path": str(path)}}))
    system["card-store"].add(Card("a", "x"))
    assert path.exists() and "layer: hub default" in system.reasons[0]


def test_importing_the_module_creates_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib
    import hubofhubs.cardstore
    importlib.reload(hubofhubs.cardstore)
    assert list(tmp_path.iterdir()) == []
