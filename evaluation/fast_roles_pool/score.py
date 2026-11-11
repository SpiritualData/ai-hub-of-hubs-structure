"""The pooled stage for the roles that resolve to the fast tier: does a tier's model do those roles' jobs as well as a stronger one?

The fast tier has no public evaluation that fits its use, so its roles' own existing cases are pooled here and every candidate model runs over the same
pool (the cases are not new: each keeps its source's label). A pooled case is one call in the form its production prompt has; the answer is read as the
label the source states.

Pooled sources, by call role of ``role_tiers.csv``:

  * request_classification: the doability judgment of a goal hand-off (9), the quest-ranking judgment that places a message (53, from two sources)
  * representative_selection: the assignee judgment of a goal hand-off (9)
  * folder_view_picking: the Folder View solution's own 41 cases, scored by its own scorer (the model arm's one fast-tier call chooses the files)

Fixed before any arm was scored (this file is the record; a change to any line below is a new version of the metric, not a tuning):

  * Score = pooled pass rate: every case counts once, so the roles weigh as their cases do (request_classification is the most frequent call).
  * A case passes when the answer equals the source's label, with the source's own pass rule (folder view: every needed file shown and no unsafe pick).
  * A reply that cannot be read counts as failed.
  * The stage reports the pooled rate and the rate per role and per kind; ``wrong_yes`` counts hand-offs of a goal the label says a person must keep.
  * Verdict on a tier: ``ADEQUATE_MARGIN`` below the reference arm's pooled rate is the lowest a tier may score and still be called adequate for its
    roles (the same 5 percent tolerance the tier minimums use for benchmark noise); the reference is the tier above's held default on the same pool.

Not pooled (no existing case set that fits one call): request_extraction, context_retrieval, card_building, web_search, learning_investigation,
liveness_review, status_narration, frame_building. Those rows keep their evidence cell as unmeasured.
What it cannot see: how a model behaves inside the whole turn; the pooled prompts are the production prompts, but the replies are scored in isolation."""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

ADEQUATE_MARGIN = 0.05
ROLES = ("request_classification", "representative_selection", "folder_view_picking")
CONSUMER = HERE / "datasets" / "consumer_cases.json"
FOLDER_CASES = HERE.parent / "folder_view" / "cases.json"


def load_cases() -> List[Dict[str, Any]]:
    """The pooled cases: the consumer's rendered cases, then every Folder View case (kept as the source wrote it, under ``args.case``)."""
    pooled = json.loads(CONSUMER.read_text(encoding="utf-8"))
    for case in json.loads(FOLDER_CASES.read_text(encoding="utf-8")):
        pooled.append(dict(id=f"pool-{case['id']}", kind="folder_pick", role="folder_view_picking", source=f"folder_view/{case['id']}",
                           args=dict(case=case), expect=dict(source_rule="recall and safety")))
    return pooled


def reply_object(text: str) -> Dict[str, Any]:
    """The first JSON object in a reply, or an empty one."""
    found = re.search(r"\{.*\}", str(text or ""), re.S)
    try:
        value = json.loads(found.group(0)) if found else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def truth(value: Any) -> Any:
    return value if isinstance(value, bool) else None


def score_prompt_case(fn, case):
    args, want, kind = case["args"], case["expect"], case["kind"]
    got = reply_object(fn(kind, dict(prompt=args["prompt"])))
    if kind == "doability":
        have = truth(got.get("ai_can_do"))
        return dict(ok=have is want["ai_can_do"], got=str(have), wrong_yes=bool(have and not want["ai_can_do"]))
    if kind == "assignee":
        who = got.get("assignee")
        who = str(who) if who not in (None, "", "null") else None
        if who is not None and who not in args["member_ids"]:
            return dict(ok=False, got=f"{who} (not a member)", wrong_yes=False)
        have = bool(got.get("ai_can_do")) and who is not None
        ok = who == want["assignee"] and have is want["ai_can_do"]
        return dict(ok=ok, got=f"{who}/{have}", wrong_yes=bool(have and not want["ai_can_do"]))
    rows = got.get("results")
    chosen: List[Any] = [None] * args["items"]
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and isinstance(row.get("item"), int) and 1 <= row["item"] <= len(chosen):
            chosen[row["item"] - 1] = str(row.get("quest_id") or "").strip() or None
    return dict(ok=chosen == want["chosen"], got=json.dumps(chosen)[:60], wrong_yes=False)


def score_folder_case(fn, case):
    from folder_view import score as folder_score
    from hubofhubs.the_intelligence.subconscious.local_file_context.folder_view.model_pick import ModelPick
    source = case["args"]["case"]

    def choose(kind, args):
        arm = ModelPick(complete=lambda system, prompt: fn("folder_pick", dict(system=system, prompt=prompt)))
        return arm.choose(args["goal"], args["context"], args["root"], args["budget"], args["trail"])
    return folder_score.score_case(choose, source)


def score_case(fn, case):
    row = score_folder_case(fn, case) if case["kind"] == "folder_pick" else score_prompt_case(fn, case)
    return dict(row, ok=bool(row["ok"]), role=case["role"], kind=case["kind"], wrong_yes=bool(row.get("wrong_yes")),
                note="" if row["ok"] else "label differs")


def share(rows) -> str:
    return f"{sum(bool(r['ok']) for r in rows)}/{len(rows)}"


def aggregate(rows):
    out = {"pooled": f"{sum(bool(r['ok']) for r in rows) / max(len(rows), 1):.3f}", "pooled_passed": share(rows)}
    for role in ROLES:
        out[f"{role}_passed"] = share([r for r in rows if r.get("role") == role])
    for kind in sorted({r.get("kind") for r in rows} - {None}):
        out[f"{kind}_passed"] = share([r for r in rows if r.get("kind") == kind])
    out["wrong_yes"] = sum(bool(r.get("wrong_yes")) for r in rows)
    return out
