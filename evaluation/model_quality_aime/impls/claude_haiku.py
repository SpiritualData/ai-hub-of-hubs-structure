"""ALTERNATIVE, claude_haiku: see runners.py for the shared prompt and the reasoning setting."""
from model_quality_aime.runners import claude_arm

PAID = False
build = claude_arm("haiku")
