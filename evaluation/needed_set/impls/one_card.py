"""BASELINE: the `one_card` grouping of `cards_from_files/broken`, scored by this component. The rule must give it no pass."""
from cards_from_files.broken.one_card import cards
from cards_from_files.score import view_function


def build(meter):
    return view_function(cards, meter)
