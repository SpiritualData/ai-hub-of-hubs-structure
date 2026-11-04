"""BASELINE: one card per folder, files in walk order. The rule must give it no pass."""
import os

from cards_from_files.baselines import grouped
from cards_from_files.score import view_function


def cards(root, files, existing):
    """The grouping, for every component that scores these baselines."""
    folders = {}
    for f in files:
        folders.setdefault(os.path.dirname(f), []).append(f)
    return grouped(root, list(folders.values()))


def build(meter):
    return view_function(cards, meter)
