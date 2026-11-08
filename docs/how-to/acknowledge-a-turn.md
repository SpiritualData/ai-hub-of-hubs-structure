# Acknowledge a turn

Tell the person their message was received before any slow work starts, and replace that line with whatever the turn sends next.

The acknowledgement is a status event (`EVENT_STATUS`) marked `data["kind"] == "ack"`. It is not an interim: a status is replaced by later events and never stored in the conversation history, while an `EVENT_INTERIM` is a partial result the reader keeps.

1. Send it from whatever first holds the turn, before any model call, context search or other slow work. The contract is `ACK_WITHIN_SECONDS` (one second) from the turn's start; a web surface adds its own connection time on top.
2. In an orchestrator run, call `emit.ack()` on the run's `Emitter` right after you build it. A second call sends nothing.
3. In a surface that holds the turn before the orchestrator does (a web endpoint), build an `Acknowledger(send)` when the request arrives and call `ack()` the moment the stream opens. `acked_after` and `within_contract` tell a test or a log whether the contract held.
4. On the wire, carry the kind with the status (for example `{"event": "status", "text": "Looking into this...", "kind": "ack"}`). `is_ack` reads a `ProgressEvent`, its `to_dict()` or such a wire dict.
5. In the client, show the acknowledgement until the next event the person can see arrives, then replace it. Do not store it.

The default wording is `ACK_TEXT`. Pass your own fixed or code-written line to `ack_event(text)` or `ack(text)`; do not spend a model call on it, since the point is that it arrives before any model work.

```python
from hubofhubs.api import Acknowledger, ack_event, is_ack

sent = []
ack = Acknowledger(sent.append)
ack.ack()              # first thing, before any slow work
assert is_ack(sent[0]) and ack.within_contract
```
