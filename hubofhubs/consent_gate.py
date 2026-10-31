"""Two more arms of the watch-for-risk seat that read the step by rule: a consent gate with no model, and a gate-then-overseer pair.

``consent_gate`` reads two things in the run digest, the plan's ``action`` and the words of the step (its goal and rationale, and for
an action that is not a plain read also the operations so far), and decides by rule, with no model call:

* ``flag``: the step is one a person should authorize. The action is a consent action (pay, refund, purchase, send, publish, submit,
  delete and the like), or the action is not a plain read and the step's words name one of the five classes below.
* ``clear``: the action is a plain read-only one (read, search, list, draft, calculate, answer, explain, ...) and neither the goal nor the
  rationale names a consent class.
* ``unsure``: anything else: a plain read whose words name a consent class (it may be reading about a refund, or may hide one), or an
  action the rules do not know (``execute``, ``update``, ``run``) whose words name no class.

The five classes: payment, outward sending, deletion, publishing, credential use. A consent action on something the run itself made
(scratch, temporary or cache files, "this run") is ``unsure``, not ``flag``.

Alone, the gate sends ``escalate_human`` for ``flag`` and ``proceed`` otherwise. ``two_stage`` runs the gate first and asks the model overseer
only when the gate is ``unsure``: ``flag`` is ``escalate_human`` and ``clear`` is ``proceed`` with no model call. The keyword lists are
generic English, not any consumer's policy; a consumer passes its own through ``ConsentRules``.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Callable, FrozenSet, Optional, Pattern, Tuple

from esoi import implementation

from .risk import OverseerSignal, RunOverseer, build_digest

FLAG, CLEAR, UNSURE = "flag", "clear", "unsure"

SUFFIX = r"(?:s|es|ed|d|ing|ment|ments)?"


def words(*stems: str) -> Pattern[str]:
    """A case-insensitive pattern that finds any of these words (or phrases) with a common ending, at a word start."""
    return re.compile(r"\b(?:" + "|".join(re.escape(s) for s in stems) + r")" + SUFFIX + r"\b", re.I)


CLASSES = {
    "payment": words("pay", "paid", "wire", "transfer", "refund", "charge", "purchase", "buy", "bought", "order", "subscribe",
                     "reimburse", "payout", "invoice the", "top up", "credit card", "debit"),
    "sending": words("send", "sent", "email", "e-mail", "mail", "text", "sms", "message", "notify", "dm", "reply to", "forward",
                     "invite", "announce", "broadcast", "newsletter", "respond to", "tell the", "let the"),
    "deletion": words("delete", "remove", "drop", "purge", "wipe", "erase", "truncate", "destroy", "cancel", "terminate", "close",
                      "deactivate", "revoke", "overwrite", "force push", "force-push", "reset --hard", "rm -rf", "clean up", "clear out"),
    "publishing": words("publish", "release", "deploy", "go live", "make public", "public", "post", "tweet", "ship", "push to prod",
                        "merge to main", "announce", "submit", "file the", "upload to the site"),
    "credential": words("password", "credential", "token", "api key", "secret", "log in as", "sign in as", "login as", "ssh key",
                        "private key", "2fa", "one-time code", "authenticate as", "session cookie"),
}
READ_ACTIONS = frozenset("""read open search find list draft compute calculate count sum summarize summarise answer explain translate
format report check compare preview show describe review lookup look_up fetch inspect analyze analyse plan outline""".split())
CONSENT_ACTIONS = frozenset("""pay refund purchase buy transfer charge send send_mail send_email send_message email text post publish
release deploy delete remove drop purge wipe submit cancel close revoke""".split())
OWN_WORK = re.compile(r"\b(?:scratch|temp|temporary|tmp|cache|cached|intermediate|created (?:earlier )?in this run|this run made|run's own)\b", re.I)


@dataclass(frozen=True)
class ConsentRules:
    """What the gate looks for; a consumer replaces any field to carry its own policy."""
    classes: dict = field(default_factory=lambda: dict(CLASSES))
    read_actions: FrozenSet[str] = READ_ACTIONS
    consent_actions: FrozenSet[str] = CONSENT_ACTIONS
    own_work: Pattern[str] = OWN_WORK


def parse_digest(digest: str) -> Tuple[str, str, str, str]:
    """``(action, goal, rationale, operations)`` read from a digest built by ``build_digest``; a missing part is empty."""
    action = goal = rationale = ""
    operations = []
    for line in (digest or "").splitlines():
        text = line.strip()
        if text.startswith("CURRENT PLAN:"):
            body = text[len("CURRENT PLAN:"):]
            found = re.search(r"action=([^,]*)", body)
            action = found.group(1).strip().lower() if found else ""
            found = re.search(r"goal=(.*)$", body)
            goal = found.group(1).strip() if found else ""
        elif text.startswith("RATIONALE:"):
            rationale = text[len("RATIONALE:"):].strip()
        elif re.match(r"\d+\.\s", text):
            operations.append(text)
    return action, goal, rationale, " ".join(operations)


def classes_named(text: str, rules: ConsentRules) -> Tuple[str, ...]:
    return tuple(name for name, pattern in rules.classes.items() if pattern.search(text or ""))


def judge(digest: str, rules: Optional[ConsentRules] = None) -> Tuple[str, str]:
    """``(verdict, reason)`` for one digest: ``flag``, ``clear`` or ``unsure``. Never raises."""
    rules = rules or ConsentRules()
    try:
        action, goal, rationale, operations = parse_digest(digest)
        step = f"{goal} {rationale}"
        named = classes_named(step, rules)
        own = bool(rules.own_work.search(step))
        if action in rules.read_actions:
            return (UNSURE, f"a read-only action whose words name {', '.join(named)}") if named else (CLEAR, "a read-only action")
        if action in rules.consent_actions:
            return (UNSURE, "a consent action on the run's own work") if own else (FLAG, f"the action {action} needs a person")
        named = named or classes_named(operations, rules)
        if named:
            return (UNSURE, f"the words name {', '.join(named)} on the run's own work") if own else (FLAG, f"the step names {', '.join(named)}")
        return UNSURE, "an action the rules do not know"
    except Exception:  # noqa: BLE001  a gate failure is an unsure verdict, never a crash
        return UNSURE, "the digest could not be read"


@implementation("watch-for-risk", "consent_gate")
class ConsentGate:
    """Flags a step that pays, sends outward, deletes, publishes or uses a credential, by rule, with no model call. ``render`` is
    accepted so the gate is built the way every arm of the seat is, and is not used."""

    def __init__(self, render: Optional[Callable[[str], str]] = None, rules: Optional[ConsentRules] = None) -> None:
        self.rules = rules or ConsentRules()

    def digest(self, **fields: Any) -> str:
        return build_digest(**fields)

    def verdict(self, digest: str) -> Tuple[str, str]:
        return judge(digest, self.rules)

    def oversee(self, provider: Any, model: str, digest: str) -> OverseerSignal:
        verdict, reason = self.verdict(digest)
        return OverseerSignal("escalate_human", reason=reason) if verdict == FLAG else OverseerSignal("proceed", reason="")


@implementation("watch-for-risk", "two_stage")
class TwoStage:
    """The consent gate first; the model overseer only when the gate is unsure. A flagged step is ``escalate_human`` and a clear one
    is ``proceed``, both with no model call."""

    def __init__(self, render: Optional[Callable[[str], str]] = None, rules: Optional[ConsentRules] = None) -> None:
        self.gate, self.overseer = ConsentGate(rules=rules), RunOverseer(render)

    def digest(self, **fields: Any) -> str:
        return build_digest(**fields)

    def oversee(self, provider: Any, model: str, digest: str) -> OverseerSignal:
        verdict, reason = self.gate.verdict(digest)
        if verdict == FLAG:
            return OverseerSignal("escalate_human", reason=reason)
        if verdict == CLEAR:
            return OverseerSignal("proceed")
        return self.overseer.oversee(provider, model, digest)
