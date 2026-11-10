"""The ``cards-from-files`` arm over Graphify's code graph: one card per community of files, no model call.

Graphify's code-only extraction (tree-sitter, no model) turns the files into a graph of symbols joined by calls, imports and
inheritance. This arm collapses that graph to a graph of files (an edge's weight is the number of symbol edges that cross
between two files), lets Graphify's own community detection cluster it, and makes one card per community. A card lists its files
most connected first, because Graphify has no order of its own inside a group; a file with no code edge is a card of its own.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from esoi import implementation

from hubofhubs.the_self.assembler.arm_needs import GRAPHIFY
from hubofhubs.the_intelligence.subconscious.local_file_context.cards_from_files.cards_from_files import changed_cards, file_card, group_card, kept_card
from hubofhubs.the_body.internal_context.card_store.context_card_extraction import path_slug

RESOLUTION = 1.0   # Graphify's default community resolution, unchanged


def file_graph(root: Path, files: Sequence[str]):
    """The weighted graph of ``files``: Graphify's symbol graph with each symbol replaced by the file that holds it."""
    import networkx as nx
    from graphify.build import build_from_json
    from graphify.extract import extract

    wanted = set(files)
    with tempfile.TemporaryDirectory(prefix="graphify_cache_") as cache:
        extraction = extract([root / f for f in files], cache_root=Path(cache), root=root, parallel=False)
    symbols = build_from_json(extraction)
    holder = {n: d.get("source_file", "") for n, d in symbols.nodes(data=True) if d.get("file_type") == "code" and d.get("source_file") in wanted}
    graph = nx.Graph()
    graph.add_nodes_from(files)
    for a, b, data in symbols.edges(data=True):
        if a in holder and b in holder and holder[a] != holder[b]:
            weight = float(data.get("weight", 1.0))
            if graph.has_edge(holder[a], holder[b]):
                graph[holder[a]][holder[b]]["weight"] += weight
            else:
                graph.add_edge(holder[a], holder[b], weight=weight)
    return graph


def file_groups(graph, files: Sequence[str]) -> List[List[str]]:
    """Graphify's communities of the file graph, each ordered by weighted degree (most connected first, then path), groups in the order
    their first file appears in ``files``, so a build is deterministic."""
    from graphify.cluster import cluster

    position = {f: i for i, f in enumerate(files)}
    groups = [sorted(members, key=lambda f: (-graph.degree(f, weight="weight"), f)) for members in cluster(graph, resolution=RESOLUTION).values()]
    return sorted(groups, key=lambda g: min(position[f] for f in g))


@implementation("cards-from-files", "graphify_files")
class GraphifyFiles:
    """One card per community of files in Graphify's file graph (code-only extraction, free and offline)."""
    REQUIRES = (GRAPHIFY,)

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]:
        base = Path(root)
        singles = {rel: file_card(base, rel) for rel in files}
        cards = []
        for members in file_groups(file_graph(base, list(files)), list(files)):
            name = path_slug(members[0]) if len(members) == 1 else "group-" + path_slug(members[0])
            cards.append(group_card(base, name, members, singles))
        return cards

    def changed(self, root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]:
        return changed_cards(root, cards)
