"""BASELINE: no overseer. Every step proceeds, which is what the model and the harness give by themselves. No model call."""
from watch_for_risk.broken.always_proceed import build  # noqa: F401
