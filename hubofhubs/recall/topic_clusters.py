"""Grouping files into topic cards without a model: greedy agglomeration over a weighted file graph, with a size cap.

``agglomerate`` joins the two groups linked by the heaviest remaining pair while the joined group stays within ``cap`` files and the
pair clears ``min_weight``; ties are broken by file name, so the same graph always gives the same groups. ``folder_chunks`` cuts
the files left over into groups of at most ``cap`` files of one folder, so that every file is reachable through a topic card and no
card is a single file unless its folder holds one file. Standard library only.
"""
from __future__ import annotations

import posixpath
from typing import Dict, List, Mapping, Sequence, Tuple

Pair = Tuple[str, str]


def add_pair(weights: Dict[Pair, float], a: str, b: str, weight: float) -> None:
    key = (a, b) if a < b else (b, a)
    weights[key] = weights.get(key, 0.0) + weight


def agglomerate(weights: Mapping[Pair, float], cap: int, min_weight: float = 0.0) -> List[List[str]]:
    """Groups of two or more files, each of at most ``cap`` files, joined from the heaviest pair down; a file is in one group."""
    members: Dict[str, List[str]] = {}   # file -> the list object of its group
    for (a, b), weight in sorted(weights.items(), key=lambda item: (-item[1], item[0])):
        if weight < min_weight:
            break
        group_a, group_b = members.get(a), members.get(b)
        if group_a is None and group_b is None:
            group = [a, b]
        elif group_a is not None and group_b is None and len(group_a) < cap:
            group_a.append(b)
            group = group_a
        elif group_b is not None and group_a is None and len(group_b) < cap:
            group_b.append(a)
            group = group_b
        elif group_a is not None and group_b is not None and group_a is not group_b and len(group_a) + len(group_b) <= cap:
            group_a.extend(group_b)
            group = group_a
        else:
            continue
        for path in group:
            members[path] = group
    unique = {id(group): group for group in members.values()}
    return sorted((sorted(group) for group in unique.values()), key=lambda group: group[0])


def folder_chunks(files: Sequence[str], cap: int) -> List[List[str]]:
    """The files cut into groups of one folder, at most ``cap`` each; pieces are of near-equal size."""
    by_folder: Dict[str, List[str]] = {}
    for path in files:
        by_folder.setdefault(posixpath.dirname(path), []).append(path)
    chunks: List[List[str]] = []
    for folder in sorted(by_folder):
        group = sorted(by_folder[folder])
        count = -(-len(group) // cap)   # pieces of near-equal size, so no piece is a lone file unless the folder holds one
        size, extra = divmod(len(group), count)
        pieces, start = [], 0
        for number in range(count):
            end = start + size + (1 if number < extra else 0)
            pieces.append(group[start:end])
            start = end
        chunks += pieces
    return chunks
