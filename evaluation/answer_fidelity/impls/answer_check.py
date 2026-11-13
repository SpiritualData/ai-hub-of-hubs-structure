"""The answer check on the fast tier, as a run uses it: ``--impl answer_check@input=original`` reads the person's own words (the check the hub runs), ``@input=paraphrase`` reads the
agent's restated goal instead (the reference that shows what reading a paraphrase costs).

The model is the one the tier table gives the ``answer_check`` role (a tier, never a model named here) and runs on the operator's Claude CLI login: no key, no API, no tools. The
check itself is ``answer_check.judge`` of the hub, unchanged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

PAID = True


def build(meter, input="original"):
    if input not in ("original", "paraphrase"):
        raise ValueError("input is original or paraphrase")
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
    from hubofhubs.the_world.tools.delegated_agent_sessions import answer_check, providers
    model = providers.model_for("anthropic", role_tiers.tier_for(answer_check.ROLE))
    meter.model = model
    engine = meter.wrap(ClaudeCliProvider(claude_path="claude"), ("answer",))

    def ask(system, prompt):
        return engine.answer([{"role": "user", "content": prompt}], model=model, system=system)

    def check(kind, args):
        return answer_check.judge(args["input"] if input == "original" else args["paraphrase"], args["answer"], ask)
    return check
