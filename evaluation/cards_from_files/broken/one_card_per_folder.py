"""BASELINE: one card per folder, files in walk order. The rule must give it no pass."""
import os

from cards_from_files.baselines import grouped
from cards_from_files.score import view_function


def build(meter):
    def cards(root, files, existing):
        folders = {}
        for f in files:
            folders.setdefault(os.path.dirname(f), []).append(f)
        return grouped(root, list(folders.values()))
    return view_function(cards, meter)
