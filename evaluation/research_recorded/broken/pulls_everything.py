"""BASELINE: the naive memory. It records every investigation and reuses the newest earlier one on the solution whatever the question, so an unrelated question is answered
with research about something else. Zero model calls."""
from research_recorded import score

from hubofhubs.the_world.learning.recorded_research import RecordedResearch


class PullsEverything(RecordedResearch):
    def earlier(self, store, question, decision, size, solutions, scope, day):
        rows = store.related(solutions, scope, day)
        return dict(rows[0], state="fresh") if rows else None


def build(meter):
    return score.adapt(PullsEverything, meter)
