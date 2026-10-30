"""Per-idea threading, where THE IDEA IS THE CARD (hubofhubs.recall.card_thread): the fail-safe parse, the duplicate-label guard,
the candidate prior, the planner hint and the priority blending of a transcript. Pure, offline, no consumer."""
import pytest

from hubofhubs.recall.card_thread import (
    ACTION_CONTINUE,
    ACTION_NEW,
    ACTION_SWITCH,
    CardCandidate,
    CardThreadContext,
    find_duplicate_label,
    lifecycle_note,
    merge_candidates,
    normalize_label,
    parse_card_thread,
    penalized_budget,
    rank_card_first,
    render_thread_hint,
    select_thread_floor,
    split_by_card,
)


# --------------------------------------------------------------------------------------------
# 3. THE FAIL-SAFE: an ambiguous topic assignment must never cost a turn.
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    None, "", "   ", 42, {"action": "switch"}, ["switch_to:x"],
    "switch_to:", "new:", "resume", "switch:card-a", "CONTINUE ALL", "card-a",
])
def test_any_garbage_continues_the_current_card(raw):
    d = parse_card_thread(raw, active_card_id="card-a", known_ids=["card-a", "card-b"])
    assert d.action == ACTION_CONTINUE
    assert d.card_id == "card-a"
    assert d.fell_back is True


def test_a_dropped_namespace_prefix_is_repaired_when_it_is_unambiguous():
    """A REAL failure, pinned. A model handed "quest:quest_rt_622dc4ed" verbatim emitted
    "switch_to:quest_rt_622dc4ed", losing the namespace. The id was unknown, the fail-safe fired,
    and the turn stayed on the wrong idea. An EXACT, unique match on the id's trailing segment is
    not a guess, so it is repaired. Two matches would be an ambiguity, and ambiguity continues."""
    d = parse_card_thread("switch_to:quest_rt_622dc4ed", active_card_id="topic:general",
                          known_ids=["topic:general", "quest:quest_rt_622dc4ed"])
    assert (d.action, d.card_id, d.fell_back) == (ACTION_SWITCH, "quest:quest_rt_622dc4ed", False)

    # Ambiguous (two known ids share the trailing segment): continue, never pick one.
    d = parse_card_thread("switch_to:plan", active_card_id="topic:general",
                          known_ids=["topic:plan", "quest:plan"])
    assert (d.action, d.card_id, d.fell_back) == (ACTION_CONTINUE, "topic:general", True)


def test_switch_to_an_unknown_card_continues_rather_than_inventing_one():
    """The planner named a card that is not on the table. Do NOT create it, do NOT guess a
    near-match: continue. Inventing a card from a hallucinated id is how a card space rots."""
    d = parse_card_thread("switch_to:card-zzz", active_card_id="card-a",
                          known_ids=["card-a", "card-b"])
    assert (d.action, d.card_id, d.fell_back) == (ACTION_CONTINUE, "card-a", True)


def test_continue_switch_and_new_parse():
    assert parse_card_thread("continue", active_card_id="card-a").action == ACTION_CONTINUE

    d = parse_card_thread("switch_to:card-b", active_card_id="card-a",
                          known_ids=["card-a", "card-b"])
    assert (d.action, d.card_id, d.fell_back) == (ACTION_SWITCH, "card-b", False)

    d = parse_card_thread("new:Launch plan for v2", active_card_id="card-a")
    assert (d.action, d.label, d.card_id, d.fell_back) == (ACTION_NEW, "Launch plan for v2",
                                                           None, False)


def test_switching_to_the_card_already_active_is_a_continue():
    """Not a rename of the same thing: switch and continue mean different things to the consumer
    (a switch moves the conversation's active card), so a self-switch must land as continue."""
    d = parse_card_thread("switch_to:card-a", active_card_id="card-a", known_ids=["card-a"])
    assert d.action == ACTION_CONTINUE and d.card_id == "card-a"


# --------------------------------------------------------------------------------------------
# The dedupe guard: "new:" must not litter the card space with twins.
# --------------------------------------------------------------------------------------------

def test_dedupe_guard_catches_the_obvious_twins():
    existing = [CardCandidate(id="topic:launch-plan", label="Launch plan"),
                CardCandidate(id="topic:sleep", label="Sleep")]
    assert find_duplicate_label("launch plan", existing) == "topic:launch-plan"
    assert find_duplicate_label("The Launch Plan!", existing) == "topic:launch-plan"
    # Multi-word containment either way is the same idea.
    assert find_duplicate_label("launch plan for v2", existing) == "topic:launch-plan"
    # A single shared word is a CATEGORY, not the same idea (the specificity discipline).
    assert find_duplicate_label("launch metrics", existing) is None
    assert find_duplicate_label("marathon training", existing) is None
    assert normalize_label("  The  Launch-Plan!! ") == "the launch plan"


# --------------------------------------------------------------------------------------------
# 2. THE PRIOR is free: it is built from the cards retrieval ALREADY scored this turn.
# --------------------------------------------------------------------------------------------

def test_merge_candidates_uses_this_turns_retrieval_and_respects_allowed_types():
    ctx = CardThreadContext(
        active_card_id="topic:sleep", active_label="Sleep",
        candidates=[CardCandidate(id="topic:general", label="General chat")],
        allowed_types=["topic", "quest"],
    )
    card_metadata = [
        {"id": "topic:launch-plan", "title": "Launch plan", "card_type": "topic"},
        {"id": "grant:team:1:quest_command.goal.create", "title": "grant", "card_type": "capability"},
        {"id": "quest:abc", "title": "Marathon quest", "card_type": "quest", "lifecycle": "completed"},
        {"id": "docs:onboarding", "title": "Docs", "card_type": ""},   # untyped: not a topic
    ]
    cands = merge_candidates(ctx, card_metadata)
    ids = [c.id for c in cands]

    assert "topic:general" in ids          # consumer candidates always pass
    assert "topic:launch-plan" in ids      # keyword/vector arm surfaced it: the free prior
    assert "quest:abc" in ids
    assert "grant:team:1:quest_command.goal.create" not in ids   # not a topic
    assert "docs:onboarding" not in ids
    # The ACTIVE card is always on the table even when nothing retrieved it this turn ("make it
    # shorter" carries none of its keywords).
    assert "topic:sleep" in ids
    assert next(c for c in cands if c.id == "quest:abc").status == "completed"


def test_thread_hint_names_the_active_card_the_candidates_and_finished_work():
    ctx = CardThreadContext(active_card_id="topic:sleep", active_label="Sleep")
    hint = render_thread_hint(ctx, [
        CardCandidate(id="topic:launch-plan", label="Launch plan", why="matched this message"),
        CardCandidate(id="quest:abc", label="Marathon quest", status="completed"),
    ])
    assert "CURRENT TOPIC: [topic:sleep] Sleep" in hint
    assert "[topic:launch-plan] Launch plan" in hint
    assert "completed" in hint


def test_lifecycle_note_marks_finished_work_as_knowledge_not_a_to_do():
    note = lifecycle_note("completed", "in June")
    assert "completed (in June)" in note
    assert "do not propose working it as if it were still open" in note
    assert "\u2014" not in note                       # no em dashes in user-facing text
    assert lifecycle_note("active") == ""        # ongoing work says nothing


# --------------------------------------------------------------------------------------------
# 4. PRIORITY BLENDING: this card's floor + a small global floor; siblings reachable, not resident.
# --------------------------------------------------------------------------------------------

def _msgs():
    """An interleaved conversation: idea A, idea B, idea A, idea C, back to A."""
    return [
        {"role": "user", "content": "A1", "card_id": "A"},
        {"role": "assistant", "content": "A1r", "card_id": "A"},
        {"role": "user", "content": "B1", "card_id": "B"},
        {"role": "assistant", "content": "B1r", "card_id": "B"},
        {"role": "user", "content": "A2", "card_id": "A"},
        {"role": "assistant", "content": "A2r", "card_id": "A"},
        {"role": "user", "content": "C1", "card_id": "C"},
        {"role": "assistant", "content": "C1r", "card_id": "C"},
    ]


def test_floor_is_this_cards_turns_plus_a_small_global_floor():
    floor = select_thread_floor(_msgs(), card_id="A", card_turns=8, global_turns=2)
    got = [m["content"] for m in floor]

    # Every turn of idea A is there, in conversation order.
    assert got[:4] == ["A1", "A1r", "A2", "A2r"]
    # The very last exchange rides the GLOBAL floor even though it belongs to another idea: that is
    # what makes "as I just said" survive an interleave. This is priority blending, not isolation.
    assert got[-2:] == ["C1", "C1r"]
    # But idea B, which is older than the global floor, is NOT resident in A's floor.
    assert "B1" not in got and "B1r" not in got


def test_an_unstamped_message_always_belongs(regression="pre-threading conversations keep their floor"):
    """A message with no card_id predates threading (or came from a surface that does not stamp).
    Dropping it would silently shrink an existing conversation's floor, so the fail-safe is KEEP."""
    msgs = [{"role": "user", "content": "old", "card_id": None},
            {"role": "user", "content": "B1", "card_id": "B"},
            {"role": "user", "content": "A1", "card_id": "A"}]
    got = [m["content"] for m in select_thread_floor(msgs, card_id="A", card_turns=8,
                                                     global_turns=1)]
    assert "old" in got and "A1" in got
    mine, others = split_by_card(msgs, card_id="A")
    assert [m["content"] for m in mine] == ["old", "A1"]
    assert [m["content"] for m in others] == ["B1"]


def test_recall_ranks_this_card_first_but_a_strong_sibling_still_gets_through():
    """The penalty is not a filter: "combine those two ideas" has to keep working."""
    items = [
        {"id": "sibling-strong", "card_id": "B", "score": 0.9},
        {"id": "mine-weak", "card_id": "A", "score": 0.5},
        {"id": "sibling-weak", "card_id": "B", "score": 0.3},
        {"id": "mine-strong", "card_id": "A", "score": 0.8},
    ]
    ranked = rank_card_first(items, card_id="A", get_card_id=lambda i: i["card_id"],
                             get_score=lambda i: i["score"], penalty=0.5)
    ids = [i["id"] for i in ranked]
    assert ids[0] == "mine-strong"          # 0.8 vs the sibling's penalized 0.45
    assert ids[1] == "mine-weak"            # 0.5 still beats the penalized 0.45
    assert "sibling-strong" in ids          # reachable, never filtered out
    assert ids.index("sibling-strong") < ids.index("sibling-weak")
    assert penalized_budget(1000, 0.5) == 500 and penalized_budget(-5) == 0
