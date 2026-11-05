"""The hub is modular for the person who calls it: one part alone, the same part with other parameters, a typed handle, their own
implementation connected to the hub's parts, and a composite that asks only for what its answer path needs. Offline, no keys, no
model: every call passes ``environ={}`` and the parts it needs are the hub's offline defaults."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
import hubofhubs  # noqa: E402
from esoi.entry import Pending  # noqa: E402
from hubofhubs.the_body.internal_context.card_store.card import Card  # noqa: E402
from hubofhubs.the_body.internal_context.card_store.cardstore import LocalCardStore  # noqa: E402
from hubofhubs.the_body.internal_context.card_store.interface import CardStore  # noqa: E402


@pytest.fixture()
def store():
    ready = hubofhubs.run(CardStore, environ={})
    ready.add(Card("rust-1-91", "Rust 1.91 was released on 2025-10-30 with new lints."))
    ready.add(Card("py-3-14", "Python 3.14 was released in October 2025."))
    return ready


def test_one_part_alone_is_a_ready_typed_handle_and_answers_its_own_query(store):
    assert isinstance(store, LocalCardStore)
    found = hubofhubs.run("card-store", "rust", provided={"card-store": store}, environ={})
    assert [card.id for card in found] == ["rust-1-91"]


def test_the_same_part_takes_other_parameters():
    files = {"rust.md": "Rust 1.91 was released with new lints.", "py.md": "Python 3.14 was released in October."}
    plain = hubofhubs.run("context-retriever", {"query": "rust lints", "files": files}, arms={"context-retriever": "bm25_body"}, environ={})
    fielded = hubofhubs.run("context-retriever", {"query": "rust lints", "files": files}, arms={"context-retriever": "bm25_fielded"}, environ={})
    assert plain and fielded and plain[0].file == fielded[0].file == "rust.md"


def test_a_persons_own_implementation_joins_the_hub_through_typed_needs(store):
    class NewestFirstRecall:
        def __init__(self, cards: CardStore):
            self.cards = cards

        def recall(self, query, limit=5):
            return sorted(self.cards.search(query, limit=limit), key=lambda card: card.id, reverse=True)

    hubofhubs.register("the-subconscious", "newest_first", NewestFirstRecall)
    found = hubofhubs.run("the-subconscious", "released", arms={"the-subconscious": "newest_first"},
                          provided={"card-store": store}, environ={})
    assert [card.id for card in found] == ["rust-1-91", "py-3-14"]


def test_the_default_recall_runs_offline_without_a_model(store):
    found = hubofhubs.run("the-subconscious", "released", provided={"card-store": store}, environ={})
    assert {card.id for card in found} >= {"rust-1-91", "py-3-14"}


def test_the_whole_hub_asks_for_nothing_up_front():
    assert hubofhubs.needs("hub-of-hubs", environ={}) == ()      # every part, World included, is built on first use: a request that needs no key runs with none
    with pytest.raises(Pending) as caught:
        hubofhubs.run("web-search", "latest Rust version", environ={})
    message = str(caught.value)
    assert "GEMINI_API_KEY" in message
    assert "claude" not in message.lower() and "HUBOFHUBS_WRITE_ROOT" not in message
