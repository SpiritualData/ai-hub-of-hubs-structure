"""The card ceilings are deterministic gates in front of every write; the per-folder number is an argument."""
from hubofhubs.recall.context_card_ceilings import apply_card_ceilings, card_folder_key


def topic(cid, *paths):
    return {"id": cid, "files": [{"path": p} for p in paths]}


def test_a_card_is_about_the_deepest_folder_its_files_share():
    assert card_folder_key(topic("a", "src/x/a.py", "src/x/b.py")) == "src/x"
    assert card_folder_key(topic("a", "src/x/a.py", "src/y/b.py")) == "src"
    assert card_folder_key(topic("a", "top.py")) == "."
    assert card_folder_key({"id": "a"}) == ""


def test_new_cards_beyond_the_per_folder_number_are_dropped_and_refreshes_are_kept():
    existing = [topic("old", "src/a.py")]
    new = [topic("old", "src/a.py"), topic("n1", "src/b.py"), topic("n2", "src/c.py"), topic("o", "docs/d.md")]
    kept = apply_card_ceilings(new, existing, per_folder=2)
    assert [c["id"] for c in kept] == ["old", "n1", "o"]


def test_zero_means_no_per_folder_cap_and_max_cards_still_binds():
    new = [topic(f"n{i}", f"src/f{i}.py") for i in range(5)]
    assert len(apply_card_ceilings(new, [], per_folder=0)) == 5
    assert len(apply_card_ceilings(new, [], per_folder=0, max_cards=3)) == 3


def test_the_default_is_eight_cards_per_folder():
    new = [topic(f"n{i}", f"src/f{i}.py") for i in range(12)]
    assert len(apply_card_ceilings(new, [])) == 8
