# Acknowledge a turn

Tell the person their message was received before any slow work starts, in two stages, and replace each line with whatever the turn sends next.

The acknowledgement is a status event (`EVENT_STATUS`) marked `data["kind"] == "ack"`. It is not an interim: a status is replaced by later events and never stored in the conversation history, while an `EVENT_INTERIM` is a partial result the reader keeps.

1. Send it from whatever first holds the turn, before any model call, context search or other slow work. The contract is `ACK_WITHIN_SECONDS` (one second) from the turn's start; a web surface adds its own connection time on top.
2. In an orchestrator run, call `emit.ack()` on the run's `Emitter` right after you build it. A second call sends nothing.
3. In a surface that holds the turn before the orchestrator does (a web endpoint), build an `Acknowledger(send)` when the request arrives and call `ack()` the moment the stream opens. `acked_after` and `within_contract` tell a test or a log whether the contract held.
4. On the wire, carry the kind with the status (for example `{"event": "status", "text": "Looking into this...", "kind": "ack"}`). `is_ack` reads a `ProgressEvent`, its `to_dict()` or such a wire dict.
5. In the client, show the acknowledgement until the next event the person can see arrives, then replace it. Do not store it.

The acknowledgement has two stages. Stage 1, the placeholder, is written by code and described above. Stage 2, the model ack, is one sentence written by one fast-tier model call (a tier, never a model name) in the representative's voice, answering what the person actually asked. Send it with `model_ack_event(text)` or `emit.model_ack(text)`; it is an ack status marked `stage: "model"`, and `ack_stage(event)` tells the two apart (a client shows the model ack's own text, and the placeholder in its own words).

6. Start the model call at the turn's start, concurrently with context assembly. The reply path never waits for it. The target is `MODEL_ACK_TARGET_SECONDS` (3 seconds) from the turn's start.
7. If the line is not ready before the turn's next beat or the final reply, or the call fails, drop it, and log and count the drop or failure. A dropped ack is never silent, and it never delays the reply.
8. The line claims nothing the turn has not found yet: it says what you will do about the request, not what you found.

The placeholder's default wording is `ACK_TEXT`. Pass your own fixed or code-written line to `ack_event(text)` or `ack(text)`; do not spend a model call on the placeholder, since the point is that it arrives before any model work. The model call belongs to stage 2 only.

```python
from hubofhubs.api import Acknowledger, ack_event, is_ack

sent = []
ack = Acknowledger(sent.append)
ack.ack()              # first thing, before any slow work
assert is_ack(sent[0]) and ack.within_contract
```
