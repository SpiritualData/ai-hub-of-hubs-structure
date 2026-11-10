"""Folder View arm ``model_pick``: the evidence arm's wider candidate list, then one fast-tier model call that picks from it. PAID.

The folder is judged and scored as in ``evidence_ranked`` with a low bar, so up to ``CANDIDATES`` likely files are listed with their first heading and
size. One completion (the hub's Claude CLI provider on the operator's login, with no tools) names the files the goal needs, one path per line; only
paths from the list are taken, in the model's order, and the files the goal names (and the flagged ones) stay as the evidence arm returned them. When
the call fails or names nothing, the evidence arm's own picks stand. Standard library plus the hub."""
from __future__ import annotations

import os
from typing import Any, Callable, List, Mapping, Optional, Sequence

from esoi import implementation

from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_intelligence.subconscious.local_file_context.folder_view import naming
from hubofhubs.the_intelligence.subconscious.local_file_context.folder_view.choice import FolderChoice, Pick
from hubofhubs.the_intelligence.subconscious.local_file_context.folder_view.evidence_ranked import EvidenceRanked, headings
from hubofhubs.the_intelligence.subconscious.local_file_context.folder_view.judgment import HEAD_CHARS, small_text

CANDIDATES = 30
SYSTEM = ("You choose which files a worker should see before starting a piece of work. You get the goal and a list of candidate files, each "
          "with its size and first heading. Reply with the paths of the files the work needs, most useful first, one path per line, exactly as listed, "
          "and nothing else. Choose few: only files the work needs.")


@implementation("folder-view", "model_pick")
class ModelPick:
    """The evidence arm's candidates, narrowed and ordered by one cheap model call."""
    REQUIRES = (needs.CLAUDE_BINARY, needs.CLAUDE_ACCOUNT, needs.CLAUDE_CLI_BOUNDARY)
    PAID = True      # every choice calls a model: never run by a free (offline) metric run

    def __init__(self, complete: Optional[Callable[[str, str], str]] = None, tier: str = "fast"):
        self.injected, self.tier = complete, tier

    def completion(self) -> Callable[[str, str], str]:
        if self.injected is not None:
            return self.injected
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
        from hubofhubs.the_world.tools.delegated_agent_sessions import providers
        engine = ClaudeCliProvider(claude_path="claude")
        model = providers.model_for("anthropic", self.tier)
        return lambda system, prompt: engine.answer([{"role": "user", "content": prompt}], model=model, system=system)

    def choose(self, goal: str, context: str, root: str, budget_chars: int = 100000, trail: Sequence[Mapping[str, Any]] = (),
               file_limit: int = 5000) -> FolderChoice:
        base = EvidenceRanked(bar=0.1, max_picks=CANDIDATES).choose(goal, context, root, budget_chars, trail, file_limit)
        fixed = [p for p in base.picks if p.named or p.flagged]
        candidates = [p for p in base.picks if not (p.named or p.flagged)]
        if len(candidates) < 2:
            return base
        lines = [f"{p.path} ({p.size} bytes) {headings(small_text(os.path.join(root, p.path), HEAD_CHARS))[:80]}" for p in candidates]
        try:
            reply = self.completion()(SYSTEM, f"GOAL:\n{goal.strip()[:1500]}\n\nCANDIDATE FILES:\n" + "\n".join(lines))
        except Exception:  # noqa: BLE001 -- a failed call leaves the evidence arm's choice
            return base
        by_path = {p.path: p for p in candidates}
        chosen: List[Pick] = []
        used = sum(p.size for p in fixed if not p.flagged)
        for line in str(reply or "").splitlines():
            path = line.strip().strip("`*-• ").split(" (")[0]
            pick = by_path.pop(path, None)
            if pick is not None and used + pick.size <= budget_chars:
                chosen.append(Pick(pick.path, "chosen by the model from the candidates" + (f" ({pick.reason})" if pick.reason else ""), pick.size))
                used += pick.size
        if not chosen:
            return base
        base.picks = fixed + chosen
        return base
