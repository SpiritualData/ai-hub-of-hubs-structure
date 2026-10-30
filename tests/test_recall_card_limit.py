"""The card limit: a number the owner chose, parsed from a raw setting, enforced by one admission function and always announced."""
import pytest

from hubofhubs.recall import card_limit
from hubofhubs.recall.card_limit import CardLimit, card_kind, parse_max_cards
from hubofhubs.recall.card_repository import FilesystemCardRepository


def topic(cid, used=0):
    return {"id": cid, "name": cid, "usage_count": used, "files": [{"path": f"{cid}.py"}], "provenance": {"created_by_task": "bootstrap"}}


def learned(cid):
    return {"id": cid, "content": [{"why": "learned"}], "provenance": {"created_by_task": "a run"}}


def managed(cid):
    return {"id": cid, "managed_by": "sync"}


def guarded(tmp_path, limit, announcer=None):
    repo = FilesystemCardRepository(str(tmp_path))
    guard = CardLimit(str(tmp_path), limit, repo=repo, cards=repo.load_all, revision=repo.revision, announcer=announcer)
    return repo, guard


def put(repo, guard, cid, card):
    victims = guard.prepare(cid, card)
    if guard.admit(cid, card, victims):
        guard.wrote(repo.write(cid, card))
        admitted = True
    else:
        admitted = False
    guard.speak()
    return admitted


@pytest.mark.parametrize("raw,expected", [(None, 1000), ("", 1000), ("250", 250), ("1,500", 1500), ("0", 0), ("Unlimited", 0),
                                          ("no-limit", 0), ("lots", 1000), ("-4", 1000)])
def test_the_limit_is_parsed_from_a_raw_setting(raw, expected):
    assert parse_max_cards(raw) == expected


def test_a_bad_setting_is_named_in_the_warning(caplog):
    with caplog.at_level("WARNING"):
        parse_max_cards("lots", name="MY_LIMIT")
    assert "MY_LIMIT" in caplog.text


def test_a_card_is_a_topic_an_import_a_learned_card_or_one_another_system_manages():
    assert card_kind(managed("m")) == card_limit.KIND_MANAGED
    assert card_kind(topic("t")) == card_limit.KIND_TOPIC
    assert card_kind(learned("l")) == card_limit.KIND_LEARNED
    assert card_kind({"id": "i", "provenance": {"imported_from": "sub"}}) == card_limit.KIND_IMPORTED


def test_at_the_limit_a_new_derived_card_is_refused_and_a_refresh_is_not(tmp_path):
    repo, guard = guarded(tmp_path, 2)
    assert put(repo, guard, "a", topic("a")) and put(repo, guard, "b", topic("b"))
    assert not put(repo, guard, "c", topic("c"))
    assert guard.refused_ids == {"c"} and repo.count() == 2
    assert put(repo, guard, "a", topic("a", used=3))
    assert repo.count() == 2


def test_a_learned_card_moves_the_coldest_unused_topic_card_out_and_nothing_is_deleted(tmp_path):
    repo, guard = guarded(tmp_path, 2)
    put(repo, guard, "used", topic("used", used=5))
    put(repo, guard, "cold", topic("cold"))
    assert put(repo, guard, "note", learned("note"))
    assert set(repo.load_all()) == {"used", "note"} and repo.quarantined("cold") is not None
    assert guard.state.evicted == 1 and guard.state.admitted_over == 0


def test_when_nothing_may_move_the_learned_card_is_kept_over_the_limit_and_counted(tmp_path):
    repo, guard = guarded(tmp_path, 2)
    put(repo, guard, "a", topic("a", used=1))
    put(repo, guard, "b", topic("b", used=1))
    assert put(repo, guard, "note", learned("note"))
    assert repo.count() == 3 and guard.state.admitted_over == 1 and guard.state.evicted == 0
    assert put(repo, guard, "m", managed("m")) and repo.count() == 4      # above the limit nothing is exchanged


def test_no_limit_admits_everything(tmp_path):
    repo, guard = guarded(tmp_path, 0)
    assert all(put(repo, guard, f"c{i}", topic(f"c{i}")) for i in range(5))


def test_the_notice_is_given_once_by_the_announcer_the_consumer_passed(tmp_path):
    card_limit.reset_announcements()
    said = []
    repo, guard = guarded(tmp_path, 1, announcer=lambda g, at_open, notify: said.append((g.limit, at_open)))
    put(repo, guard, "a", topic("a"))
    put(repo, guard, "b", topic("b"))
    put(repo, guard, "c", topic("c"))
    assert said == [(1, False)]
    assert guard.state.reached_at


def test_a_full_store_is_still_announced_in_the_log_when_no_announcer_was_passed(tmp_path, caplog):
    card_limit.reset_announcements()
    repo, guard = guarded(tmp_path, 1)
    with caplog.at_level("WARNING"):
        put(repo, guard, "a", topic("a"))
        put(repo, guard, "b", topic("b"))
    assert "card limit of 1" in caplog.text


def test_the_counters_persist_beside_the_cards(tmp_path):
    card_limit.reset_announcements()
    repo, guard = guarded(tmp_path, 1)
    put(repo, guard, "a", topic("a"))
    put(repo, guard, "b", topic("b"))
    again = CardLimit(str(tmp_path), 1, repo=repo, cards=repo.load_all, revision=repo.revision)
    assert again.state.reached_at == guard.state.reached_at
