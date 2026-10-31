"""ALTERNATIVE, deepseek_flash: see runners.py for the shared prompt and the reasoning setting."""
from model_quality_aime.runners import deepseek_arm

PAID = True
build = deepseek_arm("deepseek-flash")
