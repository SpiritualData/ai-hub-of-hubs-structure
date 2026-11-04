"""BASELINE: the `two_cards` grouping of `cards_from_files/broken`, scored by this component. The rule must give it no pass."""
from cards_from_files.broken.two_cards import cards
from cards_from_files.score import view_function


def build(meter):
    return view_function(cards, meter)
