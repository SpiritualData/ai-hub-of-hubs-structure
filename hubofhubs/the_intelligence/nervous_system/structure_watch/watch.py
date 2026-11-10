"""Structure Watch arms. ``best_tier_call`` makes one small call on the best tier over the code-built digest; ``findings_only`` raises the code's own findings with no call.

Both return the same result: ``called``, ``reason`` (``first``, ``changed``, ``unchanged``, ``off``, ``ceiling`` or ``no_model``), ``tier``, ``tier_note``, ``tokens_in``,
``tokens_out``, ``digest_hash``, ``items`` (at most ``MAX_ITEMS``, each with ``subject``, ``what``, ``why_now``, ``risk``, ``severity``, ``step`` and a ``route``) and ``suppressed`` (items
raised before and not worse). The route is decided by Judgment Calls for each item: a person's proposal (``proposal``) for structure a person wrote or reviewed or owns, what a running
experiment holds fixed and anything irreversible, or applied by the AI itself (``applied``) for structure the AI made and nobody reviewed, with ``change`` recording what, why,
before and after so it can be undone. The marks of who reviewed a record come with the structure (``review``: ``{table:id: "person" | "ai"}``); a record with no mark is a person's.
Hard caps: ``INPUT_TOKENS`` in, ``OUTPUT_TOKENS`` out, ``MAX_ITEMS`` items. Standard library plus the hub and ``esoi``."""
import json
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.understanding.solution_consideration.experiments import commitments, parts

from hubofhubs.the_intelligence.nervous_system.structure_watch.digest import (
    CHARS_PER_TOKEN, INPUT_TOKENS, SEVERITIES, digest_of, milestones_of, rows_of, snapshot, solution_of)

OUTPUT_TOKENS = 500
MAX_ITEMS = 3
KIND = "structure-watch"
ROLE = "structure-watch"
STRUCTURE_WATCH_TIER = "best"     # replaced by the role table's row for ``structure-watch`` when it is readable (the only role allowed on the best tier unasked)
SOFT_FRACTION = 0.8               # the share of a run's ceiling after which no new call starts (the run ceilings' own soft share)
IRREVERSIBLE = ("merge", "delete", "remove")
FIELDS = (("what", 160), ("why_now", 200), ("risk", 160), ("step_text", 160))
INSTRUCTION = (
    "You watch the structure of one intent (its ESOI records) against the recent and planned work. Say where the structure itself needs attention BEFORE more work is built on it. "
    "Use only the findings and records in the digest. Reply with ONLY a JSON object {\"items\": [...]} with at most 3 items, most important first; zero items is a good and common answer. "
    "Each item: {\"subject\": \"table:id taken from the digest\", \"what\": \"what in the structure needs attention\", \"why_now\": \"which recent or planned work it affects\", "
    "\"risk\": \"the risk if ignored\", \"severity\": \"low|medium|high\", \"step\": \"reevaluate|add-metric|merge|investigate|restrategize|rerun-metric|select-implementation|other\", "
    "\"step_text\": \"the proposed next step\", optional \"edit\": {\"kind\": \"spec_edit\", \"target\": \"solution id\", \"field\": \"field name\", \"value\": \"new text\"}}. "
    "Each field is one short sentence. Never use an em dash. Do not repeat what the digest already says is fine.")


def tokens_of(text: str) -> int:
    return -(-len(text) // CHARS_PER_TOKEN)


def tier_and_note() -> Dict[str, str]:
    """The tier of the role ``structure-watch`` from the hub's role table, and what to say when no arm is measured for it (it then runs on the strongest measured one)."""
    try:
        from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
        tier = role_tiers.tier_for(ROLE)
        return {"tier": tier, "call_tier": role_tiers.chooser_tier(tier), "note": role_tiers.resolution_note(tier)}
    except Exception:      # noqa: BLE001 the table is another part's: its absence leaves the one named constant
        return {"tier": STRUCTURE_WATCH_TIER, "call_tier": STRUCTURE_WATCH_TIER, "note": "the role table was not readable: the constant STRUCTURE_WATCH_TIER names the tier"}


def parse_items(raw: str, known: Sequence[str]) -> Optional[List[Dict[str, Any]]]:
    """The items of a reply: fences stripped, at most ``MAX_ITEMS``, fields clipped, an unknown severity read as medium and an item naming a record that is not in the digest dropped.
    ``None`` when the reply is not the JSON asked for (the caller then uses the code's findings); ``[]`` is a valid answer."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, Mapping) or not isinstance(data.get("items"), list):
        return None
    out = []
    for item in data["items"]:
        if not isinstance(item, Mapping) or str(item.get("subject") or "") not in known:
            continue
        clean = {"subject": str(item["subject"]), "severity": str(item.get("severity")) if str(item.get("severity")) in SEVERITIES else "medium", "step": str(item.get("step") or "other")[:30]}
        for name, limit in FIELDS:
            clean[name] = " ".join(str(item.get(name) or "").split())[:limit]
        if isinstance(item.get("edit"), Mapping):
            clean["edit"] = dict(item["edit"])
        out.append(clean)
    return out[:MAX_ITEMS]


def from_findings(found: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [{"subject": f["subject"], "severity": f["severity"], "step": f["step"], "what": f["detail"], "why_now": "affects " + (", ".join(f["affects"]) or "the intent"), "risk": "more work is built on it",
             "step_text": f["step"]} for f in found[:MAX_ITEMS]]


class Watch:
    """The shared part of the arms: the last watch, the repeat rule, the routing of each item through Judgment Calls and the record of the watch.
    ``store`` has ``add(record)`` and ``latest(limit)`` (Body's run store); ``judge`` is Judgment Calls' ``decide``; ``applier`` is ESOI Application's ``apply``; ``person`` is who is asked."""
    REQUIRES = ()     # standard library plus the hub; the model call is the ``ask`` it is given

    def __init__(self, ask: Optional[Callable[..., Any]] = None, store: Any = None, judge: Optional[Callable[..., Mapping[str, Any]]] = None,
                 applier: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None, person: str = "", off: bool = False,
                 ceilings: Optional[Mapping[str, Any]] = None):
        self.ask, self.store, self.judge, self.applier, self.person, self.off, self.ceilings = ask, store, judge, applier, person, off, dict(ceilings or {})

    def last(self) -> Mapping[str, Any]:
        for record in reversed(list(self.store.latest(50)) if self.store is not None else []):
            if record.get("kind") == KIND:
                return record
        return {}

    def ceiling_reached(self) -> bool:
        """True once the run has used the soft share of its spend or time ceiling (``spent_usd``, ``ceiling_usd``, ``elapsed_seconds``, ``ceiling_seconds``; a missing or None ceiling is unlimited)."""
        for spent, ceiling in (("spent_usd", "ceiling_usd"), ("elapsed_seconds", "ceiling_seconds")):
            limit = self.ceilings.get(ceiling)
            if isinstance(limit, (int, float)) and float(self.ceilings.get(spent) or 0.0) >= float(limit) * SOFT_FRACTION:
                return True
        return False

    def route(self, structure: Mapping[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        """Ask Judgment Calls whether this item needs a person (a proposal) or the AI applies it itself, and carry out the applied ones, recording what, why, before and after."""
        review = structure.get("review") or {}
        held = set()
        for row in rows_of(structure, "experiments"):
            if (row.get("status") or "").strip() in ("running", "reevaluating"):
                held |= {e.partition(":")[2].strip() for e in parts(row.get("links", ""))} | set(commitments(row))
        sid = solution_of(structure, item["subject"])
        why = ""
        if review.get(item["subject"], "person") != "ai":
            why = "a person wrote, reviewed or owns this record"
        elif sid and (sid in held or sid.lower() in held):
            why = "a running experiment holds it fixed"
        elif item["step"] in IRREVERSIBLE:
            why = "the step cannot be undone"
        context = {"needs_person": bool(why), "ai_owned": not why, "why": why}
        decision = self.judge({"severity": item["severity"], "reason": item["what"]}, self.person, context) if self.judge else {"decision": "ask", "to": "human"}
        item = dict(item, decision=decision.get("decision"), to=decision.get("to", ""))
        if decision.get("decision") == "proceed" and item.get("edit") and self.applier is not None:
            done = dict(self.applier({"subject": structure.get("intent", ""), "edit": item["edit"]}))
            item["route"] = "applied" if done.get("applied") else "proposal"
            item["change"] = {"what": item["what"], "why": item["why_now"], "before": done.get("before"), "after": done.get("after"), "undo": {**item["edit"], "value": done.get("before")}, "result": done}
        else:
            item["route"] = "proposal" if decision.get("decision") != "proceed" else "noted"
        return item

    def settle(self, structure: Mapping[str, Any], items: Sequence[Dict[str, Any]], before: Mapping[str, Any]) -> Dict[str, Any]:
        """Leave out items raised by the last watch and not worse; route the rest."""
        rank = {s: i for i, s in enumerate(SEVERITIES)}
        seen = {(i["subject"], i["step"]): i["severity"] for i in before.get("items") or ()}
        fresh, repeated = [], []
        for item in items:
            old = seen.get((item["subject"], item["step"]))
            (repeated if old is not None and rank[item["severity"]] <= rank.get(old, 0) else fresh).append(item)
        return {"items": [self.route(structure, i) for i in fresh], "suppressed": repeated, "considered": list(items)}

    def result(self, structure, now, text, digest_hash, before, items, called, reason, tokens_in, tokens_out, tier) -> Dict[str, Any]:
        settled = self.settle(structure, items, before)
        out = {"called": called, "reason": reason, "tier": tier["tier"] if called else "", "tier_note": tier["note"] if called else "", "tokens_in": tokens_in, "tokens_out": tokens_out,
               "digest_hash": digest_hash, "items": settled["items"], "suppressed": settled["suppressed"]}
        if self.store is not None:
            self.store.add({"id": "watch-" + re.sub(r"\D", "", str(now or structure.get("now") or ""))[:14] + f"-{digest_hash[:6]}", "kind": KIND, "time": str(now or structure.get("now") or ""), "digest_hash": digest_hash,
                            "items": settled["considered"], "tokens_in": tokens_in, "tokens_out": tokens_out, "tier": out["tier"], "snapshot": snapshot(structure),
                            "changed_at": str(now or structure.get("now") or "")})
        return out

    def prepare(self, structure: Mapping[str, Any]):
        before = self.last()
        text, digest_hash, found, changes = digest_of(dict(structure, changed_at=before.get("changed_at", "")), before.get("snapshot") or {})
        return before, text, digest_hash, found, changes


@implementation("structure-watch", "findings_only")
class FindingsOnly(Watch):
    """Raises the code's own findings (at most three, most severe first) with no model call: the free baseline the call has to beat."""

    def watch(self, structure: Mapping[str, Any], now: str = "") -> Mapping[str, Any]:
        try:
            if self.off:
                return {"called": False, "reason": "off", "items": [], "suppressed": [], "tokens_in": 0, "tokens_out": 0, "tier": "", "tier_note": "", "digest_hash": ""}
            before, text, digest_hash, found, _ = self.prepare(structure)
            if before and before.get("digest_hash") == digest_hash:
                return {"called": False, "reason": "unchanged", "items": [], "suppressed": [], "tokens_in": 0, "tokens_out": 0, "tier": "", "tier_note": "", "digest_hash": digest_hash}
            return self.result(structure, now, text, digest_hash, before, from_findings(found), False, "changed" if before else "first", 0, 0, tier_and_note())
        except Exception as error:      # noqa: BLE001 a watch never breaks the run
            return {"called": False, "reason": f"failed: {type(error).__name__}", "items": [], "suppressed": [], "tokens_in": 0, "tokens_out": 0, "tier": "", "tier_note": "", "digest_hash": ""}


@implementation("structure-watch", "best_tier_call")
class BestTierCall(Watch):
    """One call on the best tier over the digest (at most ``INPUT_TOKENS`` in, ``OUTPUT_TOKENS`` out), none when the digest is the same as the last watch's, the run is at its ceiling
    or the watch is off. A reply that is not the JSON asked for falls back to the code's findings, so a malformed reply is never silence."""

    def watch(self, structure: Mapping[str, Any], now: str = "") -> Mapping[str, Any]:
        quiet = {"called": False, "items": [], "suppressed": [], "tokens_in": 0, "tokens_out": 0, "tier": "", "tier_note": "", "digest_hash": ""}
        try:
            if self.off:
                return dict(quiet, reason="off")
            before, text, digest_hash, found, _ = self.prepare(structure)
            if before and before.get("digest_hash") == digest_hash:
                return dict(quiet, reason="unchanged", digest_hash=digest_hash)
            if self.ask is None:
                return dict(quiet, reason="no_model", digest_hash=digest_hash)
            if self.ceiling_reached():
                return dict(quiet, reason="ceiling", digest_hash=digest_hash)
            tier = tier_and_note()
            prompt = INSTRUCTION + "\n\n" + text
            prompt = prompt[: INPUT_TOKENS * CHARS_PER_TOKEN]
            reply = self.ask(prompt, tier["call_tier"], OUTPUT_TOKENS)
            raw = reply.get("text", "") if isinstance(reply, Mapping) else str(reply or "")
            tokens_in = int(reply.get("tokens_in") or 0) if isinstance(reply, Mapping) and reply.get("tokens_in") else tokens_of(prompt)
            tokens_out = int(reply.get("tokens_out") or 0) if isinstance(reply, Mapping) and reply.get("tokens_out") else tokens_of(raw)
            known = set(snapshot(structure)) | {f["subject"] for f in found} | {f"milestones:{m['id']}" for m in milestones_of(structure)}
            items = parse_items(raw[: OUTPUT_TOKENS * CHARS_PER_TOKEN], known)
            return self.result(structure, now, text, digest_hash, before, from_findings(found) if items is None else items, True, "changed" if before else "first", tokens_in, min(tokens_out, OUTPUT_TOKENS), tier)
        except Exception as error:      # noqa: BLE001 a watch never breaks the run
            return dict(quiet, reason=f"failed: {type(error).__name__}")
