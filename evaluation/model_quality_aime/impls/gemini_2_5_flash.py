"""ALTERNATIVE, gemini_2_5_flash: see runners.py for the shared prompt and the reasoning setting."""
from model_quality_aime.runners import gemini_arm

PAID = True
build = gemini_arm("gemini-2.5-flash")
