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


def test_records_supplied_as_rows_form_the_same_network():
    from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import SolutionNetwork
    tables = {
        "intents": [{"intent_id": "top", "name": "Top", "implements": ""}, {"intent_id": "growth", "name": "Growth", "implements": "reach:plan"}],
        "solutions": [{"solution_id": "reach", "intent_id": "top", "name": "Reach", "purpose": "Reach new readers.", "milestones": "1. 1000 subscribers"},
                      {"solution_id": "weekly-video", "intent_id": "growth", "name": "Weekly Video", "purpose": "Publish one video each week.",
                       "knowledge": "[lesson] Short titles did better (source: last month's results)"}],
    }
    network = SolutionNetwork.from_rows(tables)
    found = RecordsIndex().relevant("publish the weekly video", network)["solutions"]
    assert found[0]["solution_id"] == "weekly-video" and found[0]["chain"] == ["reach"]
    made = network.prompt("weekly-video", "publish it")
    assert "Publish one video each week." in made["text"] and made["knowledge"][0]["claim"].startswith("Short titles")


def test_the_gate_keeps_only_solutions_at_or_above_the_threshold_fixed_from_the_relevance_cases():
    import json
    from hubofhubs.the_intelligence.subconscious.relevant_solutions.gate import DEFAULT_MIN_SCORE, selected, threshold_from_cases
    assert [f["solution_id"] for f in selected([{"solution_id": "a", "score": 80}, {"solution_id": "b", "score": 20}], 73)] == ["a"]
    cases = json.loads((ROOT / "evaluation" / "relevant_solutions" / "cases.json").read_text())
    arm = RecordsIndex()
    points = [(f["score"], f["solution_id"] in set(c["expect"]["gold"])) for c in cases for f in arm.relevant(c["args"]["text"], str(ROOT))["solutions"]]
    assert abs(threshold_from_cases(points) - DEFAULT_MIN_SCORE) <= 2      # the default is the rule's answer on the hub's own cases, give or take the point the records' growth since it was fixed moved it (74 on 2026-11-08, fixed at 73)
