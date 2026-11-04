"""BASELINE: two cards, the test files and the rest, each in walk order. The rule must give it no pass."""
from cards_from_files.baselines import grouped
from cards_from_files.score import view_function
from hubofhubs.recall.context_card_extraction import is_test_path


def build(meter):
    def cards(root, files, existing):
        return grouped(root, [[f for f in files if is_test_path(f)], [f for f in files if not is_test_path(f)]])
    return view_function(cards, meter)
