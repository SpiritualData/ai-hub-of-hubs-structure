"""The hub's default card store: a small local SQLite store (in memory, or one file) that keeps ``Card`` objects.

The first real executing implementation in the hub. Standard library only; opens nothing at import. The default path is
``:memory:``, so the default install needs no setting; a consumer that wants a file passes ``options={"card-store":
{"path": "..."}}`` in its config.
"""
import json
import sqlite3
import threading
from typing import List, Optional

from esoi import implementation

from .card import Card
from . import arm_needs as needs

SCHEMA = "CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, text TEXT NOT NULL, source TEXT NOT NULL, tags TEXT NOT NULL)"


def row_card(row) -> Card:
    return Card(id=row[0], text=row[1], source=row[2], tags=tuple(json.loads(row[3])))


@implementation("card-store", "local_card_store")
class LocalCardStore:
    """Keeps cards in SQLite. Search matches every word of the query as a case-insensitive substring of the text."""
    REQUIRES = ()     # standard library sqlite3

    def __init__(self, path: str = ":memory:"):
        self.path = path
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(SCHEMA)
        self.db.commit()

    def add(self, card: Card) -> str:
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?)",
                            (card.id, card.text, card.source, json.dumps(list(card.tags))))
            self.db.commit()
        return card.id

    def get(self, card_id: str) -> Optional[Card]:
        with self.lock:
            row = self.db.execute("SELECT id, text, source, tags FROM cards WHERE id = ?", (card_id,)).fetchone()
        return row_card(row) if row else None

    def search(self, query: str = "", limit: int = 10, tag: str = "") -> List[Card]:
        words = [w.lower() for w in query.split() if w]
        with self.lock:
            rows = self.db.execute("SELECT id, text, source, tags FROM cards ORDER BY id").fetchall()
        found = [row_card(r) for r in rows]
        found = [c for c in found if all(w in c.text.lower() for w in words) and (not tag or tag in c.tags)]
        return found[:max(0, limit)]

    def delete(self, card_id: str) -> bool:
        with self.lock:
            done = self.db.execute("DELETE FROM cards WHERE id = ?", (card_id,)).rowcount
            self.db.commit()
        return bool(done)

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM cards").fetchone()[0]

    def close(self) -> None:
        with self.lock:
            self.db.close()
