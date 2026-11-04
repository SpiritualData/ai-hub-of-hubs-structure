"""affinity_tags: the SOFT sibling of ``scope_tags``. Ranking only, it never hides anything.

THE SPLIT
---------
  * ``scope_tags``    = WHO MAY SEE an item (hard fence: audience, tenant, privacy). A fenced item is
                        gone from the turn's candidates.
  * ``affinity_tags`` = WHAT AN ITEM IS ABOUT (soft: a project, a topic, a grouping). It only nudges
                        the score of an item that is already visible, so something learned under one
                        grouping can still answer a turn focused on another (or under none) when
                        it is exactly what the turn needs, while the turn's focus is
                        preferred.

THE CONCEPT
-----------
An item MAY carry ``affinity_tags: ["<kind>:<id>", ...]``; a turn MAY carry the same vocabulary in
its ``meta["affinity_tags"]``. This module does not mint or parse the vocabulary and knows nothing
about what a kind means: it only compares tag sets.

THE FACTOR
----------
``affinity_factor(item_tags, turn_tags, home_boost=..., away_factor=...)`` is the one pure function
every ranking arm multiplies into its score, right where scores are formed and AFTER the hard fence:

  * either side has NO tags -> 1.0 (no information, no change);
  * the tag sets intersect -> ``home_boost`` (> 1 prefers the turn's focus);
  * otherwise -> ``away_factor`` (<= 1; 1.0 means no penalty).

Both defaults are 1.0, so an arm that does not configure them ranks bit-for-bit as before. Arms apply
the factor to ORDERING only, never to a relevance floor, so affinity cannot admit or hide an item.

Never raises: malformed input or a non-numeric weight degrades to 1.0.
"""
from __future__ import annotations

from typing import List

from .scope_tags import ScopeTags, as_tag_list


def affinity_factor(item_tags: ScopeTags, turn_tags: ScopeTags, *, home_boost: float = 1.0,
                    away_factor: float = 1.0) -> float:
    """Score multiplier for an item with ``item_tags`` seen by a turn with ``turn_tags``. Never raises."""
    try:
        item_list = as_tag_list(item_tags)
        turn_list = as_tag_list(turn_tags)
        if not item_list or not turn_list:
            return 1.0
        if not set(item_list).isdisjoint(turn_list):
            return float(home_boost)
        return float(away_factor)
    except Exception:  # noqa: BLE001
        return 1.0


def affinity_label(item_tags: ScopeTags) -> str:
    """A short provenance string for an item's tags (``"project:x, topic:y"``), '' when untagged.
    Never raises."""
    try:
        return ", ".join(as_tag_list(item_tags))
    except Exception:  # noqa: BLE001
        return ""


def affinity_tags_of(item: object) -> List[str]:
    """The ``affinity_tags`` of a dict-like item as a clean list ([] when absent). Never raises."""
    try:
        return as_tag_list(item.get("affinity_tags"))  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        return []
