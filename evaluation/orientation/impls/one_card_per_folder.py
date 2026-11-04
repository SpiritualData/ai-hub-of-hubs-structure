"""BASELINE: the `one_card_per_folder` grouping of `cards_from_files/broken`, scored by this component. The rule must give it no pass."""
from orientation.score import view_function
from cards_from_files.broken.one_card_per_folder import cards


def build(meter):
    return view_function(cards, meter)
