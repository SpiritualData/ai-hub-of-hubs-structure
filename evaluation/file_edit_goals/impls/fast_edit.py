"""``fast_edit`` on the Claude CLI provider (the operator's subscription login, no key), at the tier named by ``FILE_EDIT_TIER`` (fast, balanced or quality; default
fast) or by the arm name (``fast_edit@tier=balanced``). The model is the one the tier chooser names on the day of the run, never a name in this file, and it is
what the results row records, so the role tier table can match a recorded run to the tier's model."""
from file_edit_goals.score import DayChooser, SandboxWriter, claude_provider, tier_of

PAID = True


def build(meter, tier=None):
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.tier_registry import TierRegistry
    from hubofhubs.the_world.tools.file_editing.fast_edit import FastEditRunner
    tier = tier_of(tier)
    provider, model = claude_provider(meter, tier)

    def run(kind, args):
        runner = FastEditRunner(provider=provider, writer=SandboxWriter(args["root"]), registry=TierRegistry(DayChooser()))
        return runner.run_goal(goal=args["goal"], brief=args["goal"], model=model)
    return run
