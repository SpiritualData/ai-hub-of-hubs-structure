"""Relevant Solutions and the briefs the Subconscious prepares, on the hub's own public records (no model call)."""
from pathlib import Path

from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_intelligence.subconscious.cards_from_files.knowledge_cards import QUARANTINED, cards_of
from hubofhubs.the_intelligence.subconscious.context_retriever.knowledge_pick import pick
from hubofhubs.the_intelligence.subconscious.solution_briefs import briefs
from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import network_of, split_knowledge
from hubofhubs.the_intelligence.subconscious.relevant_solutions.records_index import RecordsIndex

ROOT = Path(__file__).resolve().parents[5]
REQUEST = "Should Cards From Files switch to the Graphify arm?"


def test_a_request_about_one_solution_names_it_with_its_chain_and_dependents():
    found = RecordsIndex().relevant(REQUEST, str(ROOT))["solutions"]
    assert found[0]["solution_id"] == "cards-from-files"
    assert found[0]["chain"] == ["the-subconscious", "the-intelligence"]
    assert "card-store" in found[0]["dependents"]


def test_the_prompt_holds_the_recorded_loss_and_knowledge_is_apart_from_the_stable_part():
    made = network_of(str(ROOT)).prompt("cards-from-files", REQUEST)
    assert "graphify_files: passed 3 of 63" in made["text"]
    assert not any(line.startswith("Knowledge: ") for line in made["text"].splitlines())
    assert made["knowledge"] and all(item["status"] == "active" for item in made["knowledge"])


def test_knowledge_reaches_the_prompt_by_mode():
    network = network_of(str(ROOT))
    found = RecordsIndex().relevant(REQUEST, str(ROOT))["solutions"][:1]
    none = briefs(network, found, REQUEST, "none")["solutions"][0]
    every = briefs(network, found, REQUEST, "all")["solutions"][0]
    assert "Knowledge that bears on this" not in none["prompt"] and none["knowledge_picked"] == []
    assert len(every["knowledge_picked"]) == every["knowledge_total"] > 0
    assert set(briefs(network, found, REQUEST, "all")["ancestors"]) == {"the-subconscious", "the-intelligence"}


def test_the_retriever_picks_a_person_item_always_and_a_quarantined_item_never():
    items = split_knowledge("s1", "Graph arms lost on our cases.\nTopic cards name what a person searches for.")
    items.append({"id": "k-s1-p", "claim": "Keep cards per topic", "source_kind": "person", "source": "a person", "solution_ids": ["s1"], "status": "active"})
    cards = cards_of("s1", {"text": "stable", "knowledge": items, "knowledge_inactive": [{**items[0], "id": "k-s1-old", "status": "superseded"}]})
    assert any(QUARANTINED in c.tags for c in cards)

    class FirstOnly:
        def retrieve(self, query, files, budget_tokens=4000):
            return [{"file": next(k for k in files if "graph" in files[k].lower())}]

    active = [c for c in cards if "knowledge" in c.tags and QUARANTINED not in c.tags]
    picked = [c.id for c in pick("graph arm", active, FirstOnly())]
    assert picked[0] == "knowledge-k-s1-p" and "knowledge-k-s1-1" in picked and "knowledge-k-s1-2" not in picked
    assert "knowledge-k-s1-old" not in [c.id for c in active]
    assert isinstance(cards[0], Card) and "managed" in cards[0].tags
