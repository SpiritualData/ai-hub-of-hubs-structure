"""scope_tags: one generic cross-arm fence so a context item scoped to one tenant-like grouping
(a project, a workspace, a team) never answers a turn scoped to a different one.

THE PROBLEM
-----------
A consumer that runs one assistant across many projects (or workspaces, or teams) needs a fact
learned while working in project X to stay out of an answer given inside project Y. Several retrieval
arms persist and re-surface items across turns and conversations (a recent-context store, a per-card
vector store, a keyword card store); this is the one shared notion of "this item belongs to that
project" versus "this turn is asking about a different project".

THE CONCEPT
-----------
An item (a card, a vector hit, a recent-context record) MAY carry ``scope_tags: ["<kind>:<id>",
...]``. A turn MAY carry the same vocabulary in its ``meta``/``context_meta`` under the
``"scope_tags"`` key. The vocabulary is whatever a consumer's scope keys already are
(``"<kind>:<id>"``); this module does not mint or parse the vocabulary, it only compares tag sets.

THE FENCE RULE
--------------
``scope_tags_allow(item_tags, turn_tags)`` is the single pure predicate every arm applies:

  * the item has NO tags -> visible everywhere (untagged is legacy data / general knowledge, never
    hidden by this fence);
  * the turn has NO tags -> the caller isn't scoping this turn to anything, so nothing is hidden;
  * otherwise -> visible only when the two tag sets intersect.

This is deliberately a POST-filter, not a payload-level exact-match query: a vector store's own
``scope`` filter (a tenant/user id) is a hard, indexed, single-value partition, while scope_tags is a
many-valued, optional, itemwise membership check applied to whatever the store already returned.

Never raises: any malformed input degrades to the safest reading for that side (an unparseable item
tag list is empty, so the item defaults to being visible, and nothing is raised since inputs are
just normalized).
"""
from __future__ import annotations

from typing import Any, List, Optional, Sequence, Union

ScopeTags = Optional[Union[str, Sequence[str]]]


def as_tag_list(tags: ScopeTags) -> List[str]:
    """Normalize ``tags`` (a bare string, a list/tuple, or None/falsy) into a deduped list of
    non-empty strings. Never raises."""
    try:
        if not tags:
            return []
        if isinstance(tags, str):
            return [tags] if tags else []
        return list(dict.fromkeys(str(t) for t in tags if t))
    except Exception:  # noqa: BLE001
        return []


def scope_tags_allow(item_tags: ScopeTags, turn_tags: ScopeTags) -> bool:
    """True when ``item_tags`` should be visible to a turn carrying ``turn_tags``.

    True when the item has no tags, or the turn has no tags, or the two tag sets intersect. Never
    raises."""
    try:
        item_list = as_tag_list(item_tags)
        if not item_list:
            return True
        turn_list = as_tag_list(turn_tags)
        if not turn_list:
            return True
        return not set(item_list).isdisjoint(turn_list)
    except Exception:  # noqa: BLE001
        return True


def scope_tags_from_keys(scope_keys: ScopeTags, kinds: Sequence[str]) -> List[str]:
    """The keys among ``scope_keys`` whose kind (the text before the first ``":"``) is in
    ``kinds``, in order, deduped. A bare key with no ``":"`` (e.g. ``"global"``, or a bare
    conversation id passed directly) has no kind and never becomes a tag. ``kinds`` is the consumer's
    choice: the kinds of key the fence exists to isolate.

    This is the single, shared way every scope-key-consuming module derives its ``scope_tags``
    (the keys "in scope this turn") from a list of scope keys such as ``["conv:a", "project:x",
    "global"]`` with ``kinds=("project",)`` -> ``["project:x"]``. Never raises.
    """
    out: List[str] = []
    try:
        kind_set = set(kinds or ())
        for key in as_tag_list(scope_keys):
            if ":" not in key:
                continue
            kind = key.split(":", 1)[0]
            if kind in kind_set and key not in out:
                out.append(key)
    except Exception:  # noqa: BLE001
        return out
    return out


def union_scope_tags(*tag_sources: ScopeTags) -> List[str]:
    """Union several scope-tag sources into one deduped list, preserving first-seen order. Any
    falsy/malformed source contributes nothing. Never raises."""
    out: List[str] = []
    try:
        for source in tag_sources:
            for tag in as_tag_list(source):
                if tag not in out:
                    out.append(tag)
    except Exception:  # noqa: BLE001
        return out
    return out
