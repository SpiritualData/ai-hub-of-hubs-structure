"""ALTERNATIVE, gpt_5_mini: see runners.py for the shared prompt and the reasoning setting."""
from model_quality_aime.runners import openai_arm

PAID = True
build = openai_arm("gpt-5-mini")
