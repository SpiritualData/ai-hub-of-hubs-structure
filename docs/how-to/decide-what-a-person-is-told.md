# Decide what a person is told while a turn runs

The Mind emits everything it does as events (plan, read, partial, status, interim, milestone, decision, result). It never decides what reaches the person. One policy in Consciousness does, the same for every surface: `communicate(event, turn)` returns a `Delivery`.

| Delivery | What the person gets | Kept in history | Example |
|---|---|---|---|
| `DELIVER_NOTHING` | nothing; the event stays in the transparency stream, inspectable on demand | no | a plan, a read, a model chunk, token counts |
| `DELIVER_STATUS` | a line shown now and replaced by whatever comes next | no | the acknowledgement, a phase change, a partial result after a short stretch |
| `DELIVER_DURABLE` | a message they would want to see if they came back later | yes | the final answer; a usable partial result after a long stretch, with another long stretch to come |
| `DELIVER_ASK` | a message plus a notification | yes | the run is blocked on them; a finding the Mind marked `data["notify"] = True` |

1. Build a `TurnCommunicator()` when the turn starts. It keeps the clock and when the last kept message went out.
2. Send the acknowledgement first, before any slow work (see [Acknowledge a turn](acknowledge-a-turn.md)).
3. For each event, call `talk.decide(event, expected_remaining_seconds=...)` (leave the estimate out when nobody knows) and act on `delivery.kind`: draw a status that replaces the last one, store a message, store an ask and notify, or draw nothing.
4. Pass `CommunicationPolicy(long_stretch_seconds=...)` to change what counts as a long stretch (default `LONG_STRETCH_SECONDS`, 30 seconds).

Every decision reads structure only: the event's type, its `final`, `done` and `notify` data, the elapsed time since the last kept message, and the expected remaining time. It never reads the words.

```python
from hubofhubs.api import DELIVER_DURABLE, EVENT_INTERIM, ProgressEvent, TurnSoFar, communicate

event = ProgressEvent(type=EVENT_INTERIM, text="Found 12 of 40 rows so far.", data={"final": False})
assert communicate(event, TurnSoFar(elapsed_seconds=45.0)).kind == DELIVER_DURABLE
```
