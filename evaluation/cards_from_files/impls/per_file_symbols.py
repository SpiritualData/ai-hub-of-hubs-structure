"""One card per file, described by its docstrings and symbols: an index of files, not a card builder."""
from cards_from_files.score import adapt
from hubofhubs.recall.cards_from_files import PerFileSymbols


def build(meter):
    return adapt(PerFileSymbols, meter)
