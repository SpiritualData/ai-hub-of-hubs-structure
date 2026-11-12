"""Rebuild cases.json for Long-Term Memory: invented, neutral cases of what a memory must do (source tag ``invented-neutral``: no consumer data).

    python3 evaluation/long_term_memory/build_cases.py

A case retains dated items for people, then recalls for a query at a fixed clock, and expects the ids recalled in order. The rules: a request recalls the
items that share its subject; an unrelated or content-free request recalls nothing; the newer item leads on equal relevance; a clearly better match outranks a
weaker newer one; one person's items never reach another; an item past the retention period is gone; the limit holds; the same id retained twice is one item;
a short word inside a longer one is no match; a paraphrase that shares no word is recalled (only a meaning-based arm can; no arm here reads meaning). Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-07-12T09:00:00Z"


def item(ident, text, at, person="ana", scope_tags=(), affinity_tags=()):
    return {"id": ident, "text": text, "at": at, "person": person, "scope_tags": list(scope_tags), "affinity_tags": list(affinity_tags)}


def case(name, items, query, expect, person="ana", limit=5, scope_tags=(), affinity_tags=()):
    return {"id": "memory-" + name, "source": "invented-neutral", "kind": "recall",
            "args": {"items": items, "query": query, "person": person, "limit": limit, "now": NOW,
                     "scope_tags": list(scope_tags), "affinity_tags": list(affinity_tags)}, "expect": expect}


def main():
    garden = item("g", "We planned the vegetable garden beds and chose tomato seedlings", "2026-07-01T10:00:00Z")
    taxes = item("t", "The tax return needs the donation receipts from March", "2026-07-02T10:00:00Z")
    trip = item("r", "Booked the train to the coast for the second weekend of August", "2026-07-03T10:00:00Z")
    cases = [
        case("topical-match", [garden, taxes, trip], "how many tomato seedlings did we choose", ["g"]),
        case("second-topic", [garden, taxes, trip], "which receipts does the tax return need", ["t"]),
        case("unrelated-recalls-nothing", [garden, taxes, trip], "explain how volcanoes erupt", []),
        case("content-free-follow-up", [garden, taxes, trip], "what about it", []),
        case("empty-store", [], "tomato seedlings", []),
        case("newer-leads-on-equal-relevance", [item("old", "Ordered tomato seedlings from the nursery", "2026-05-01T10:00:00Z"), item("new", "Ordered tomato seedlings from the market", "2026-07-10T10:00:00Z")],
             "tomato seedlings order", ["new", "old"]),
        case("better-match-outranks-weaker-newer", [item("strong", "Quarterly budget review: marketing budget, hiring budget and travel budget", "2026-06-01T10:00:00Z"), item("weak", "Budget meeting moved to Friday", "2026-07-11T10:00:00Z")],
             "marketing budget review hiring travel", ["strong", "weak"]),
        case("other-person-never-recalled", [garden, item("g2", "Planted tomato seedlings along the fence", "2026-07-05T10:00:00Z", "ben")], "tomato seedlings", ["g"]),
        case("other-person-sees-only-their-own", [garden, item("g2", "Planted tomato seedlings along the fence", "2026-07-05T10:00:00Z", "ben")], "tomato seedlings", ["g2"], person="ben"),
        case("unknown-person-recalls-nothing", [garden, taxes], "tomato seedlings", [], person="cho"),
        case("past-retention-is-gone", [item("ancient", "Chose tomato seedlings for the garden", "2025-12-01T10:00:00Z"), item("fresh", "Watered the tomato seedlings", "2026-07-09T10:00:00Z")],
             "tomato seedlings", ["fresh"]),
        case("limit-holds", [item(f"i{n}", f"Tomato seedlings batch number {n}", f"2026-07-0{n}T10:00:00Z") for n in range(1, 6)], "tomato seedlings batch", ["i5", "i4"], limit=2),
        case("same-id-is-one-item", [item("x", "Tomato seedlings need sun", "2026-07-01T10:00:00Z"), item("x", "Tomato seedlings need sun and water", "2026-07-02T10:00:00Z")], "tomato seedlings sun", ["x"]),
        case("partial-overlap-still-recalled", [garden, taxes, trip], "tomato advice for this weekend", ["r", "g"]),
        case("unreadable-time-ranks-oldest", [item("odd", "Tomato seedlings note", "not a date"), item("ok", "Tomato seedlings note", "2026-07-01T10:00:00Z")], "tomato seedlings note", ["ok"]),
        case("word-inside-another-word-is-not-a-match", [item("pty", "Planned the party menu and the guest list", "2026-07-04T10:00:00Z")], "art classes", []),
        case("paraphrase-shares-no-word", [item("p", "The vegetable patch is ready for its first sowing", "2026-07-04T10:00:00Z")], "when do we begin planting the garden", ["p"]),
        # a subject may be an AI representative (even one with no person behind it); an item may carry the scope of the work it came from
        case("rep-recalls-its-own-earlier-work", [item("w", "Reviewed the citations for chapter three", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q1"])], "citations for chapter three", ["w"], person="rep:bailey", scope_tags=["quest:q1"]),
        case("rep-never-sees-another-reps-items", [item("w", "Reviewed the citations for chapter three", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q1"])], "citations for chapter three", [], person="rep:batman", scope_tags=["quest:q1"]),
        case("character-with-no-person-recalls-its-own", [item("c", "Told the guest the lighthouse is closed on Sundays", "2026-07-04T10:00:00Z", "rep:gandalf")], "is the lighthouse open on Sunday", ["c"], person="rep:gandalf"),
        case("fence-hides-an-item-from-a-scope-the-asker-cannot-open", [item("a", "Tomato seedlings plan", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q1"]), item("b", "Tomato seedlings budget", "2026-07-04T10:00:00Z", "rep:bailey", ["quest:q2"])], "tomato seedlings", ["a"], person="rep:bailey", scope_tags=["quest:q1"]),
        case("turn-with-several-scopes-sees-each", [item("a", "Tomato seedlings plan", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q1"]), item("b", "Tomato seedlings budget", "2026-07-04T10:00:00Z", "rep:bailey", ["quest:q2"])], "tomato seedlings", ["b", "a"], person="rep:bailey", scope_tags=["quest:q1", "quest:q2"]),
        case("affinity-prefers-the-selected-scope-and-still-reaches-another", [item("a", "Tomato seedlings plan", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q1"], ["quest:q1"]), item("b", "Tomato seedlings budget", "2026-07-04T10:00:00Z", "rep:bailey", ["quest:q2"], ["quest:q2"])], "tomato seedlings", ["a", "b"], person="rep:bailey", scope_tags=["quest:q1", "quest:q2"], affinity_tags=["quest:q1"]),
        case("affinity-never-crosses-the-access-fence", [item("z", "Tomato seedlings plan", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q9"], ["quest:q9"])], "tomato seedlings", [], person="rep:bailey", scope_tags=["quest:q1", "quest:q2"], affinity_tags=["quest:q9"]),
        case("a-turn-with-no-scope-sees-no-scoped-item", [item("z", "Tomato seedlings plan", "2026-07-03T10:00:00Z", "rep:bailey", ["quest:q1"])], "tomato seedlings", [], person="rep:bailey"),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
