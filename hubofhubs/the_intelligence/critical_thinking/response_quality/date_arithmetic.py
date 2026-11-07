"""Dates a response states, held to the calendar: the date arithmetic a model keeps getting wrong, checked by code.

Two checks, both pure arithmetic on dates the text itself states (never on its wording):

* "N days from today" beside one calendar date is wrong when N is not the real distance from the turn's own today (the date the evidence states, else the server's date with
  one day of slack for the person's zone);
* "N days before/after <event> (D)" is wrong when D is not N days from the date the same paragraph states just before it.

``dates_in`` reads every calendar date a text states (day and month, either order, ranges, ISO dates) so other checks can compare dates too. The arm ``date_arithmetic`` reports
each wrong count as a finding; a wrong count has no safe automatic repair (which number is wrong is unknown), so its ``repair`` returns the response as given.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence, Tuple

from esoi import implementation

SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"\u201c(*\[])|\n+")

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
MONTH_NUMBER = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}
DAY_THEN_MONTH = re.compile(
    rf"\b(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?(?:\s*[-–]\s*(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?)?\s+(?:of\s+)?"
    rf"(?P<mon>(?:{MONTHS})[a-z]*)\b\.?", re.IGNORECASE)
MONTH_THEN_DAY = re.compile(
    rf"\b(?P<mon>(?:{MONTHS})[a-z]*)\.?\s+(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?(?:\s*[-–]\s*(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?)?\b",
    re.IGNORECASE)
ISO_DATE = re.compile(r"(?<!\d)(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})(?!\d)")


def month_of(token: str) -> Optional[int]:
    return MONTH_NUMBER.get(token.lower()[:3])


def dates_in(text: str) -> List[Tuple[str, List[Tuple[int, int]]]]:
    """Every calendar date the text states, as ``(the text of it, [(day, month), ...])`` (a range lists each endpoint)."""
    found: List[Tuple[str, List[Tuple[int, int]]]] = []
    spans: List[Tuple[int, int]] = []
    for rx in (DAY_THEN_MONTH, MONTH_THEN_DAY):
        for m in rx.finditer(text or ""):
            month = month_of(m.group("mon"))
            if month is None or any(a < m.end() and m.start() < b for a, b in spans):
                continue
            days = [int(m.group("d1"))] + ([int(m.group("d2"))] if m.group("d2") else [])
            if any(not 1 <= d <= 31 for d in days):
                continue
            spans.append((m.start(), m.end()))
            found.append((m.group(0).strip(" ."), [(d, month) for d in days]))
    for m in ISO_DATE.finditer(text or ""):
        month, day = int(m.group("m")), int(m.group("d"))
        if 1 <= month <= 12 and 1 <= day <= 31:
            found.append((m.group(0), [(day, month)]))
    return found


FROM_TODAY = re.compile(r"(?<!\d)(?P<n>\d{1,3})\s+days?\s+(?:away\s+)?from\s+(?:today|now)\b", re.IGNORECASE)
TODAY_IN_EVIDENCE = re.compile(r"(?:today|current date|now)\b[^\n\d]{0,40}(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})", re.IGNORECASE)
LIVE_DATE_LINE = re.compile(r"Date:\s*(?:[A-Za-z]+,\s*)?(?P<mon>[A-Za-z]+)\s+(?P<d>\d{1,2}),\s*(?P<y>\d{4})")


def today_of(evidence: str):
    """(today, tolerance in days): the date the turn's own context states, else the server's date with one day of slack
    (the person's zone may be a day away from the server's)."""
    from datetime import date
    match = TODAY_IN_EVIDENCE.search(evidence or "")
    try:
        if match:
            return date(int(match.group("y")), int(match.group("m")), int(match.group("d"))), 0
        live = LIVE_DATE_LINE.search(evidence or "")
        if live and month_of(live.group("mon")):
            return date(int(live.group("y")), month_of(live.group("mon")), int(live.group("d"))), 0
    except ValueError:
        pass
    return date.today(), 1


def day_count_errors(draft: str, evidence: str) -> List[str]:
    """Each "N days from today" the draft states beside a calendar date when N is not the real distance from the turn's own
    today to that date. Pure arithmetic on dates the text states (never on its wording): the model keeps miscounting these.
    Only the explicit "from today / from now" form is judged, because "3 days before they arrive" counts from another date."""
    from datetime import date
    today, slack = today_of(evidence)
    errors: List[str] = []
    for sentence in SENTENCE_END.split(draft or ""):
        claim = FROM_TODAY.search(sentence)
        found = dates_in(sentence)
        if not claim or len(found) != 1 or len(found[0][1]) != 1:
            continue
        day, month = found[0][1][0]
        try:
            target = date(today.year, month, day)
        except ValueError:
            continue
        if target < today:
            continue
        real = (target - today).days
        if abs(int(claim.group("n")) - real) > slack:
            errors.append(f"{real} days from today to {found[0][0]}, not {claim.group('n')}")
    return errors


RELATIVE_TO_EVENT = re.compile(
    r"(?<!\d)(?P<n>\d{1,3})\s+days?\s+(?P<dir>before|after)\s+(?P<event>[A-Za-z][A-Za-z' ]{2,30}?)\s*\((?P<when>[^()]{3,25})\)",
    re.IGNORECASE)


def event_offset_errors(draft: str) -> List[str]:
    """Each "N days before/after <event> (D)" whose D is not the date N days from the date the SAME paragraph states just
    before it (IMP-027: "arrive 13 Nov ... 3 days before arrival (17 Nov)" when 3 days before 13 Nov is 10 Nov). Pure date
    arithmetic on dates the text states; it judges only this explicit parenthesised form, and only when a date comes earlier in
    the paragraph to count from."""
    from datetime import date, timedelta
    errors: List[str] = []
    for paragraph in (draft or "").split("\n\n"):
        for claim in RELATIVE_TO_EVENT.finditer(paragraph):
            earlier = dates_in(paragraph[:claim.start()])
            stated = dates_in(claim.group("when"))
            if not earlier or len(stated) != 1 or len(stated[0][1]) != 1 or len(earlier[-1][1]) != 1:
                continue
            (sd, sm), (ed, em) = stated[0][1][0], earlier[-1][1][0]
            try:
                year = date.today().year
                anchor, claimed = date(year, em, ed), date(year, sm, sd)
            except ValueError:
                continue
            n = int(claim.group("n"))
            expected = anchor - timedelta(days=n) if claim.group("dir").lower() == "before" else anchor + timedelta(days=n)
            if claimed != expected:
                errors.append(f"{n} days {claim.group('dir').lower()} {earlier[-1][0]} is {expected.day} "
                              f"{expected:%b}, not {stated[0][0]}")
    return errors


@implementation("response-quality", "date_arithmetic")
class DateArithmetic:
    """A response holds when each day count it states is the real distance between the dates it names."""
    REQUIRES = ()     # pure functions

    def judge(self, response: str, evidence: str = "", profile: Optional[Any] = None) -> Sequence[str]:
        """The wrong counts, unless the profile lists no such criterion."""
        if profile is not None and getattr(profile, "criterion", None) and profile.criterion("faithfulness to evidence") is None:
            return []
        return self.critique(response, evidence)

    def critique(self, answer: str, evidence: str = "") -> Sequence[str]:
        return list(day_count_errors(answer, evidence)) + list(event_offset_errors(answer))

    def repair(self, response: str, evidence: str = "") -> str:
        return response
