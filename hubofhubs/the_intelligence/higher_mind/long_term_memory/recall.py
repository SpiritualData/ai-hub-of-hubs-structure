"""Long-Term Memory arms: keep what happened across requests as dated items per person, drop them after a retention period, and recall the ones that bear on a
request. An item is a mapping with ``text``, optionally ``id`` and ``at`` (an ISO time). A person's items are kept apart: nothing retained for one person is
recalled for another.

``file_recall`` keeps one JSON file per person and ranks by the share of the query's keywords an item contains, damped by age (the score halves every
``half_life_days``), the newer ahead on a tie; an item that shares no keyword is not recalled, so an unrelated request recalls nothing. ``card_store_recall`` keeps
the items as cards in the Card Store (the person as the card's tag, the time as its source) and finds them with the store's own search, one keyword at a time,
ranked the same way; it builds on the store and so inherits its substring matching. ``recent_window`` is the bound: the newest items whatever the request says, which is
what a chat history window gives. Standard library plus the hub and ``esoi``."""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_body.internal_context.card_store.interface import CardStore
from hubofhubs.the_body.internal_context.card_store.text_sampling import keywords_from_text

MAX_AGE_DAYS = 180.0
HALF_LIFE_DAYS = 60.0


def parse(raw: Any) -> datetime:
    """An ISO time as an aware datetime; an unreadable or empty one is the epoch, so it ranks oldest and is never kept as new."""
    text = str(raw or "").strip()
    try:
        moment = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return datetime.fromtimestamp(0, timezone.utc)
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def stamp(now: str) -> str:
    return now or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def age_days(at: str, now: str) -> float:
    return max(0.0, (parse(stamp(now)) - parse(at)).total_seconds() / 86400.0)


def made(item: Mapping[str, Any], now: str = "") -> Dict[str, Any]:
    """The stored form of an item: ``id`` (a hash of the text and time when none was given), ``text`` and ``at``."""
    text, at = str(item.get("text") or ""), str(item.get("at") or stamp(now))
    return {"id": str(item.get("id") or hashlib.sha1(f"{at}|{text}".encode()).hexdigest()[:16]), "text": text, "at": at}


def ranked(query: str, items: Sequence[Mapping[str, Any]], now: str, half_life_days: float, limit: int, overlaps: Optional[Mapping[str, int]] = None) -> List[Dict[str, Any]]:
    """The items that bear on the query, best first: the share of the query's keywords in the item (or the given ``overlaps`` count) times the age damping, newer first on a tie."""
    wanted = set(keywords_from_text(query))
    scored = []
    for item in items:
        shared = overlaps.get(item["id"], 0) if overlaps is not None else len(wanted & set(keywords_from_text(item["text"])))
        if wanted and shared:
            scored.append((shared / len(wanted) * 0.5 ** (age_days(item["at"], now) / half_life_days), parse(item["at"]), item))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [dict(row[2]) for row in scored[:limit]]


@implementation("long-term-memory", "file_recall")
class FileRecall:
    """One file per person; recall by keyword share damped by age; items older than the retention period are dropped."""
    REQUIRES = ()     # standard library

    def __init__(self, directory: str = "", max_age_days: float = MAX_AGE_DAYS, half_life_days: float = HALF_LIFE_DAYS):
        self.directory = Path(directory or tempfile.mkdtemp(prefix="long-term-memory-"))
        self.max_age_days, self.half_life_days = max_age_days, half_life_days

    def path(self, person: str) -> Path:
        return self.directory / f"{hashlib.sha1(person.encode()).hexdigest()[:16]}.json"

    def load(self, person: str, now: str = "") -> List[Dict[str, Any]]:
        try:
            items = json.loads(self.path(person).read_text())
        except (OSError, ValueError):
            return []
        return [i for i in items if age_days(i["at"], now) <= self.max_age_days]

    def retain(self, item: Mapping[str, Any], person: str = "") -> str:
        stored = made(item)
        items = [i for i in self.load(person, stored["at"]) if i["id"] != stored["id"]] + [stored]
        self.directory.mkdir(parents=True, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        with os.fdopen(handle, "w") as out:
            json.dump(items, out)
        os.replace(temp, self.path(person))
        return stored["id"]

    def recall(self, query: str, person: str = "", limit: int = 5, now: str = "") -> Sequence[Mapping[str, Any]]:
        return ranked(query, self.load(person, now), now, self.half_life_days, limit)


@implementation("long-term-memory", "card_store_recall")
class CardStoreRecall:
    """Items kept as Card Store cards (the person as tag, the time as source) and found by the store's own search, one keyword at a time."""
    REQUIRES = ()     # the Card Store it is handed

    def __init__(self, store: CardStore, max_age_days: float = MAX_AGE_DAYS, half_life_days: float = HALF_LIFE_DAYS):
        self.store, self.max_age_days, self.half_life_days = store, max_age_days, half_life_days

    def retain(self, item: Mapping[str, Any], person: str = "") -> str:
        stored = made(item)
        return self.store.add(Card(id=f"{person}|{stored['id']}", text=stored["text"], source=stored["at"], tags=(f"person:{person}",)))

    def recall(self, query: str, person: str = "", limit: int = 5, now: str = "") -> Sequence[Mapping[str, Any]]:
        found: Dict[str, Dict[str, Any]] = {}
        overlaps: Dict[str, int] = {}
        for word in set(keywords_from_text(query)):
            for card in self.store.search(word, limit=100000, tag=f"person:{person}"):
                if age_days(card.source, now) > self.max_age_days:
                    continue
                found[card.id] = {"id": card.id.split("|", 1)[1], "text": card.text, "at": card.source}
                overlaps[found[card.id]["id"]] = overlaps.get(found[card.id]["id"], 0) + 1
        return ranked(query, list(found.values()), now, self.half_life_days, limit, overlaps)


@implementation("long-term-memory", "recent_window")
class RecentWindow(FileRecall):
    """The newest items of the person whatever the request says: the bound a chat history window gives."""

    def recall(self, query: str, person: str = "", limit: int = 5, now: str = "") -> Sequence[Mapping[str, Any]]:
        return sorted(self.load(person, now), key=lambda i: parse(i["at"]), reverse=True)[:limit]
