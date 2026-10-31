"""Conversation sources for cards: the source entry, the new card, and the origin stamp on write."""
import json

from hubofhubs.recall.conversation_card_builder import ConversationCardBuilder


def test_a_conversation_becomes_a_source_with_its_turn_count(tmp_path):
    builder = ConversationCardBuilder(str(tmp_path / "cards"))
    source = builder.build_conversation_source("c1", {"turns": [1, 2, 3]}, "c1.json")
    assert source["type"] == "conversation" and source["turn_count"] == 3 and len(source["sha256"]) == 64


def test_a_new_card_carries_the_source_and_a_blank_title(tmp_path):
    card = ConversationCardBuilder(str(tmp_path / "cards")).create_card_with_conversation(
        "c1", {"messages": [1], "model_hint": "m"}, "c1.json")
    assert card["id"] == "c1" and card["title"] == "" and card["sources"][0]["id"] == "c1"
    assert card["provenance"]["model"] == "m"


def test_write_card_stamps_the_origin_only_when_one_is_given(tmp_path):
    stamped = ConversationCardBuilder(str(tmp_path / "a"), origin="st_o").write_card({"id": "x"})
    plain = ConversationCardBuilder(str(tmp_path / "b")).write_card({"id": "x"})
    assert json.loads(stamped.read_text())["origin"] == "st_o"
    assert "origin" not in json.loads(plain.read_text())
