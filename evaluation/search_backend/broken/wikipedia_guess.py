"""BASELINE: no search. It guesses the Wikipedia article named by the first capitalised word of the question. Zero calls."""
import re


def build(meter):
    def run(kind, args):
        words = re.findall(r"\b[A-Z][a-z]+\b", args["question"])
        return [("https://en.wikipedia.org/wiki/" + (words[1] if len(words) > 1 else "Main_Page"), "")]
    return run
