"""Shared by the three naive baselines of ``broken/``: cards made from a fixed grouping of the files, described the way the floor
describes each file, so a baseline differs from the floor only in how it groups and in the order of the files inside a card."""
from pathlib import Path

from hubofhubs.the_intelligence.subconscious.local_file_context.cards_from_files.cards_from_files import file_card, group_card


def grouped(root, groups):
    """One card per non-empty group, the files in the order the group lists them."""
    base = Path(root)
    members = [m for g in groups for m in g]
    singles = {rel: file_card(base, rel) for rel in members}
    return [group_card(base, f"baseline-{i:04d}", g, singles) for i, g in enumerate(groups) if g]
