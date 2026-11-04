"""BASELINE: every file in one card, in walk order. The rule must give it no pass: the first three files of the view are the first three files walked."""
from cards_from_files.baselines import grouped
from cards_from_files.score import view_function


def build(meter):
    return view_function(lambda root, files, existing: grouped(root, [list(files)]), meter)
