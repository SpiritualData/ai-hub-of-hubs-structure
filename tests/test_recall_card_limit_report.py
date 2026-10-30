"""The limit's notice and report: counted from the cards, fitted to a screen, worded by the consumer's Voice."""
from pathlib import Path

from hubofhubs.recall import card_limit
from hubofhubs.recall import card_limit_report as report
from hubofhubs.recall.card_limit_report import Breakdown, Voice
from hubofhubs.recall.card_repository import FilesystemCardRepository


def voice(**kw):
    return Voice(how_to_change_line=lambda: "Tidy it, or raise the limit",
                 change_instructions=lambda cards_dir, repo: ["First, tidy it.", f"Then raise it for {cards_dir.name}."],
                 lane_note=lambda lines, guard: "About the store, not this task: " + lines[0],
                 report_command=lambda cards_dir: f"report --cards-dir {cards_dir}", **kw)


def topic(cid, path):
    return {"id": cid, "files": [{"path": path}], "provenance": {"created_by_task": "bootstrap"}}


def cards():
    out = {f"t{i}": topic(f"t{i}", f"{'alpha' if i < 2 else 'beta'}/f{i}.py") for i in range(4)}
    out["imp"] = {"id": "imp", "provenance": {"origin_store": "st", "origin_id": "x", "origin_root": "sub"}}
    out["lrn"] = {"id": "lrn", "content": [{"why": "w"}], "provenance": {"created_by_task": "a run"}}
    out["mgd"] = {"id": "mgd", "managed_by": "sync"}
    return out


def test_the_breakdown_counts_each_kind_and_groups_topics_by_top_folder(tmp_path):
    b = report.breakdown(cards(), tmp_path, 7)
    assert (b.topic, b.imported, b.learned, b.managed, b.total) == (4, 1, 1, 1, 7)
    assert b.topic_by_folder == [("alpha", 2), ("beta", 2)] and b.imported_by_source == [("sub", 1)]
    assert [row["id"] for row in b.coldest][:1] and all(row["kind"] in ("topic", "imported") for row in b.coldest)


def test_the_count_line_always_fits_one_screen_line_with_all_four_counts():
    for total in (9, 1234, 56789, 1_234_567):
        b = Breakdown(limit=total, total=total, topic=total, imported=total, learned=total, managed=total)
        line = report.count_line(b, voice())
        assert len(line) <= report.SCREEN_CHARS and ("managed" in line or "mgd" in line)


def test_a_store_over_its_limit_says_so_and_the_consumers_word_for_managed_cards_is_used():
    b = Breakdown(limit=5, total=12, topic=12)
    quest = voice(count_words=(("topic", "imported", "learned", "quest"), ("top", "imp", "lrn", "qst")))
    assert report.count_line(b, quest) == "Store over limit 5 (12): 12 topic, 0 imported, 0 learned, 0 quest"


def test_the_notice_is_the_count_line_then_the_consumers_how_to_change_line(tmp_path):
    b = report.breakdown(cards(), tmp_path, 7)
    assert report.notice_lines(b, voice()) == [report.count_line(b, voice()), "Tidy it, or raise the limit"]


def test_the_report_names_the_state_and_carries_the_consumers_steps(tmp_path):
    b = report.breakdown(cards(), tmp_path, 7)
    text = report.render_report(b, card_limit.LimitState(reached_at="then"), tmp_path, voice(managed_row_label="From elsewhere"))
    assert "# Card limit report" in text and "| From elsewhere | 1 |" in text and "First, tidy it." in text
    assert "- First reached: then" in text and "| alpha | 2 |" in text


def test_report_for_reads_the_folder_when_it_is_given_no_cards(tmp_path):
    repo = FilesystemCardRepository(str(tmp_path))
    for cid, card in cards().items():
        repo.write(cid, card)
    text = report.report_for(str(tmp_path), 3, voice())
    assert "Cards in the index: 7 (over the limit; nothing is removed to fit it)" in text


def test_announcing_writes_the_report_and_holds_a_note_for_the_next_task(tmp_path):
    card_limit.reset_announcements()
    repo = FilesystemCardRepository(str(tmp_path))
    for cid, card in cards().items():
        repo.write(cid, card)
    guard = card_limit.CardLimit(str(tmp_path), 3, repo=repo, cards=repo.load_all, revision=repo.revision)
    shown = []
    report.announce_full(guard, voice(), notify=shown.append)
    assert len(shown) == 2 and (tmp_path / report.REPORT_NAME).exists()
    assert card_limit.take_task_notes()[0].startswith("About the store, not this task: ")
    assert card_limit.take_task_notes() == []


def test_a_repository_that_cannot_set_a_card_aside_is_told_why_learned_cards_stay():
    class Hosted:
        pass

    class Guard:
        repo = Hosted()

    assert not report.can_set_aside(Guard()) and report.can_set_aside(type("G", (), {"repo": FilesystemCardRepository("/tmp/x")})())
