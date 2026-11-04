"""BASELINE: one card per file, described by its docstrings and symbols. A floor for finding a file, not a card builder: a card per file is an index of files and must never be the cards a store keeps."""
from cards_from_files.score import adapt
from hubofhubs.recall.cards_from_files import PerFileSymbols


def build(meter):
    return adapt(PerFileSymbols, meter)
