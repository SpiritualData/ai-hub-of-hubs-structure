"""No overseer. Every step proceeds, which is what the model and the harness give by themselves. No model call."""
ALTERNATIVE = True   # a diagnostic bound, ranked on the same number as every arm and never excluded by a mark
from watch_for_risk.broken.always_proceed import build  # noqa: F401
