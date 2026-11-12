"""The after-run code check calls a file missing or a figure unsupported only when it cannot account for it: it looks where the goal and the text point, and it does not
resume a session for a total it cannot check. Each test fails on the check as it was before (a path judged only against the working folder, every figure absent from a source
listed as certain). Free: no model call."""
from pathlib import Path

from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import worth_resuming
from hubofhubs.the_world.tools.delegated_agent_sessions.code_check import COULD_NOT_VERIFY, NO_SOURCE, NOT_IN_FOLDER, unsupported


def make(root: Path, files):
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    return str(root)


def test_a_path_relative_to_a_folder_the_goal_names_is_found(tmp_path):
    root = make(tmp_path, {"corpus/logs/ship/2025-01.md": "voyage 12 carried 40 t", "answers.md": "Source: logs/ship/2025-01.md"})
    goal = "Paths are relative to the corpus folder."
    assert unsupported(root, ["answers.md"], goal=goal) == []
    assert unsupported(root, ["answers.md"]) != []                    # with no word about where paths start, the check cannot know and says so


def test_a_base_folder_the_deliverable_itself_states_is_used(tmp_path):
    root = make(tmp_path, {"data/ports/a/q1.md": "tally 15", "report.md": "All paths below are under data/ports.\nSee a/q1.md"})
    assert unsupported(root, ["report.md"]) == []


def test_a_file_that_exists_nowhere_is_still_a_finding(tmp_path):
    root = make(tmp_path, {"corpus/real.md": "text", "answers.md": "See logs/ghost/2025-01.md and corpus/real.md"})
    assert unsupported(root, ["answers.md"], goal="Paths are relative to corpus.") == [f"answers.md: names the file logs/ghost/2025-01.md, which {NOT_IN_FOLDER}"]


def test_a_path_under_another_root_the_goal_names_is_not_missing(tmp_path):
    other = tmp_path / "other"
    make(other, {"pkg/records/solutions.csv": "id\n1\n"})
    work = tmp_path / "work"
    work.mkdir()
    root = make(work, {"diag.txt": "read pkg/records/solutions.csv and " + str(other / "pkg/records/solutions.csv")})
    assert unsupported(root, ["diag.txt"]) != []                                                  # without the goal the places are unknown
    assert unsupported(root, ["diag.txt"], goal=f"Check the records under {other}. Change nothing there.") == []
    assert unsupported(root, ["diag.txt"], roots=[str(other)]) == []                              # a caller that gave the session the folder says so as well


def test_a_pattern_fragment_is_not_a_file(tmp_path):
    root = make(tmp_path, {"a.md": "x", "r.md": "The files match `*-tally.md` in each port."})
    assert unsupported(root, ["r.md"]) == []


def test_a_total_that_shows_its_working_is_not_listed(tmp_path):
    root = make(tmp_path, {"src.md": "voyage 11: 4400\nvoyage 12: 5500", "out.md": "Total timber: 4400 + 5500 + 7700 = 17600"})
    assert unsupported(root, ["out.md"]) == []


def test_a_total_with_no_working_says_could_not_verify_and_the_session_is_not_resumed(tmp_path):
    root = make(tmp_path, {"src.md": "voyage 11: 4400", "out.md": "Q1 answer: 19950"})
    found = unsupported(root, ["out.md"], goal="What is the total tonnage of all voyages?")
    assert found and all(COULD_NOT_VERIFY in x and NO_SOURCE not in x for x in found)
    assert worth_resuming(root, found) == [] and worth_resuming(root, found, "named_files") == []
    assert worth_resuming(root, found, "always") == found                                         # a caller may still ask for every finding


def test_a_plain_figure_in_no_source_is_still_certain_when_nothing_asked_for_a_calculation(tmp_path):
    root = make(tmp_path, {"src.md": "the gate opens at 0800", "out.md": "The gate code is 7731."})
    found = unsupported(root, ["out.md"], goal="Write the gate details.")
    assert found == [f"out.md: the figure 7731 {NO_SOURCE}"] and worth_resuming(root, found) == found
