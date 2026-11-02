"""The English words of the terminal blocks, one flat table keyed like the Quest app's English pack.

The keys and values are copied from a consumer's English pack so a person sees the same sentence in the app and in a terminal.
`tests/test_terminal_drift.py` compares this table with that pack (and the rules with its TypeScript source) when the sibling
checkout is present and fails when they differ. Plural forms are `key_one` and `key_other`; `{name}` placeholders use the pack's
`{{name}}` spelling and are filled by `say`. A profile can pass `overrides` to say the same thing in its own words.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

EN: dict = {
    'workTrace.summarySearched_one': 'Searched the web, found {{count}} result',
    'workTrace.summarySearched_other': 'Searched the web, found {{count}} results',
    'workTrace.summaryFoundPapers_one': 'Found {{count}} paper',
    'workTrace.summaryFoundPapers_other': 'Found {{count}} papers',
    'workTrace.summary.recordsOne': 'Used your record: {{a}}',
    'workTrace.summary.recordsTwo': 'Used your records: {{a}} and {{b}}',
    'workTrace.summary.recordsMore': 'Used "{{a}}" and {{count}} more of your records',
    'workTrace.summary.sitesOne': 'Read {{a}}',
    'workTrace.summary.sitesTwo': 'Read {{a}} and {{b}}',
    'workTrace.summary.sitesMore': 'Read {{a}} and {{count}} more sites',
    'workTrace.summary.sites_one': 'Read {{count}} site',
    'workTrace.summary.sites_other': 'Read {{count}} sites',
    'workTrace.summary.papersOne': 'Checked the abstract of a paper by {{a}}',
    'workTrace.summary.papersTwo': 'Checked abstracts of papers by {{a}} and {{b}}',
    'workTrace.summary.papersMore': 'Checked abstracts of papers by {{a}} and {{count}} more',
    'workTrace.summary.papers_one': 'Checked the abstract of {{count}} paper',
    'workTrace.summary.papers_other': 'Checked abstracts of {{count}} papers',
    'workTrace.summary.records_one': 'Used {{count}} record',
    'workTrace.summary.records_other': 'Used {{count}} records',
    'workTrace.summary.recordsTeamOne': "Used the team's record: {{a}}",
    'workTrace.summary.recordsTeamTwo': "Used the team's records: {{a}} and {{b}}",
    'workTrace.summary.recordsTeamMore_one': 'Used the team\'s record "{{a}}" and {{count}} more record',
    'workTrace.summary.recordsTeamMore_other': 'Used the team\'s record "{{a}}" and {{count}} more records',
    'workTrace.group.records': 'From your Quest',
    'workTrace.group.recordsShared': "From your team's Quest",
    'workTrace.group.sources': 'Sites',
    'workTrace.group.papers': 'Papers',
    'workTrace.removedLinks_one': 'Left out {{count}} link I could not verify',
    'workTrace.removedLinks_other': 'Left out {{count}} links I could not verify',
    'workTrace.removedLinksOne': 'Left out a link to {{a}} that I could not verify',
    'workTrace.removedLinksTwo': 'Left out links to {{a}} and {{b}} that I could not verify',
    'workTrace.removedLinksSame_one': 'Left out {{count}} link to {{a}} that I could not verify',
    'workTrace.removedLinksSame_other': 'Left out {{count}} links to {{a}} that I could not verify',
    'workTrace.removedLinksMore_one': 'Left out links to {{a}} and {{count}} more that I could not verify',
    'workTrace.removedLinksMore_other': 'Left out links to {{a}} and {{count}} more that I could not verify',
    'workTrace.couldNotOpen_one': '{{count}} site could not be opened',
    'workTrace.couldNotOpen_other': '{{count}} sites could not be opened',
    'workTrace.notice.slower': 'Switched to a backup model, so this took a little longer.',
    'workTrace.notice.generic': 'Something took a little longer than usual.',
    'workTrace.recordsUntitled_one': 'and {{count}} more without a title',
    'workTrace.recordsUntitled_other': 'and {{count}} more without a title',
    'workTrace.showAll': 'Show all {{count}}',
    'workTrace.newestSite': 'Opened {{value}}',
    'workTrace.lookingRecords': 'Looking through records',
    'workTrace.recordKind.quest': 'Quest',
    'workTrace.recordKind.reflection': 'Reflection',
    'workTrace.recordKind.goal': 'Goal',
    'workTrace.recordKind.note': 'Note',
    'replyUpdates.interim.label': 'Progress so far',
    'replyUpdates.interim.labelA11y': 'Progress so far, not the final answer',
    'replyUpdates.interim.whyLabel': 'Still needed',
    'replyUpdates.interim.nextLabel': 'Next',
    'replyUpdates.earlier.collapsed': 'Earlier updates ({{count}})',
    'replyUpdates.earlier.askedOf': 'Asked {{name}}',
    'replyUpdates.earlier.askedOfYou': 'Asked you',
    'replyUpdates.earlier.askedOfUnnamed': 'Asked a teammate',
    'replyUpdates.ask.needsYou': 'Needs you',
    'replyUpdates.ask.needsYouA11y': 'This needs your answer',
    'replyUpdates.ask.waitingOn': 'Waiting on {{name}}',
    'replyUpdates.ask.waitingOnUnnamed': 'Waiting on a teammate',
    'replyUpdates.ask.waitingOnA11y': 'Waiting on {{name}} to answer',
    'replyUpdates.ask.withdraw': 'Withdraw',
    'replyUpdates.ask.withdrawing': 'Withdrawing',
    'replyUpdates.ask.withdrawn': 'You withdrew this question.',
    'replyUpdates.ask.expired': 'This question was closed without an answer.',
    'replyUpdates.ask.answerLabel': 'Your answer',
    'replyUpdates.ask.answerPlaceholder': 'Type your answer',
    'replyUpdates.ask.send': 'Send answer',
    'replyUpdates.ask.approve': 'Approve',
    'replyUpdates.ask.decline': 'Decline',
    'replyUpdates.ask.notNow': 'Not now',
    'replyUpdates.ask.loading': 'Loading the question',
    'replyUpdates.ask.silenceHold': 'I will wait for you. Not now keeps this open under Asks for you.',
    'replyUpdates.ask.silenceProceed': 'If you do nothing, this goes ahead on its own. Not now keeps it open until then.',
    'replyUpdates.ask.answeredYou': 'You answered',
    'replyUpdates.ask.answeredBy': '{{name}} answered',
    'replyUpdates.ask.answeredPlain': 'Answered',
    'replyUpdates.ask.approvedYou': 'You approved this',
    'replyUpdates.ask.approvedBy': '{{name}} approved this',
    'replyUpdates.ask.declinedYou': 'You declined this',
    'replyUpdates.ask.declinedBy': '{{name}} declined this',
    'replyUpdates.ask.auto': 'This went ahead on its own.',
    'replyUpdates.ask.resumes': 'Picking this back up with the answer.',
    'replyUpdates.ask.saved': 'Answer saved.',
    'replyUpdates.ask.error': 'Could not send that. Try again.',
    'replyUpdates.ask.errorWithdraw': 'Could not withdraw that. Try again.',
    'replyUpdates.ask.foldedTitle': 'Waiting for your answer',
    'replyUpdates.ask.foldedBody': 'Still open under Asks for you.',
    'replyUpdates.ask.answerNow': 'Answer now',
    'replyUpdates.ask.somethingElse': 'Something else',
    'replyUpdates.ask.elsePlaceholder': 'Tell me what you would like instead',
    'replyUpdates.stopped.budget': 'I stopped here because this was taking more than I could spend on one reply.',
    'replyUpdates.stopped.stalled': 'I stopped here because my last few tries were not getting anywhere.',
    'replyUpdates.stopped.attempt_cap': 'I stopped here after the most tries I can make on one reply.',
    'replyUpdates.stopped.tool_fault': 'I stopped here because something I needed to use failed.',
    'replyUpdates.stopped.continue': 'Continue',
    'replyUpdates.stopped.continueA11y': 'Continue from where this stopped',
    'questAIScreen.continueAnalysis.message': 'Continue',
}


def say(key: str, overrides: Optional[Mapping[str, str]] = None, /, **params: Any) -> str:
    """The sentence for ``key`` with ``{{name}}`` filled from ``params``. A numeric ``count`` picks ``key_one`` or ``key_other``.

    ``overrides`` (a profile's own words) win over the table. A missing key raises ``KeyError``: a renderer never shows a raw key.
    """
    table = dict(EN, **(overrides or {}))
    value = table.get(key)
    count = params.get("count")
    if value is None and isinstance(count, (int, float)):
        value = table.get(f"{key}_{'one' if count == 1 else 'other'}")
    if value is None:
        value = table.get(f"{key}_other")
    if value is None:
        raise KeyError(key)
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(params[m.group(1)]), value)


def has(key: str) -> bool:
    return key in EN or f"{key}_other" in EN
