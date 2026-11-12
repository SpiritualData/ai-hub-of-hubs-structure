"""The six words a reply uses when it applies structure, each with one meaning, and the note that tells a writer how to use them. Standard library only.

A person who has never heard of the framework should understand a reply that uses these words, so each is used in a sentence that makes its meaning clear from
context, never as a bare label, and the words are used the same way in every conversation so people come to know them by use. Other words are not banned; the
rule is only that a term keeps its one meaning and is not swapped for a synonym."""
from typing import Tuple

#: (term, the one meaning it keeps). The meaning is for the writer; the reply says it in its own sentence.
TERMS: Tuple[Tuple[str, str], ...] = (
    ("problem", "what stands in the way of the person's ideal"),
    ("ideal", "what good looks like for the person here"),
    ("solution", "the approach chosen for one problem"),
    ("alternatives", "the different ways to carry out one solution, to be compared"),
    ("metric", "the one measure that shows which alternative works"),
    ("milestone", "the next target on a solution, in terms of its metric"),
)


def vocabulary_note() -> str:
    """The standing note a writer is given when a reply applies structure."""
    meanings = "; ".join(f"{term}: {meaning}" for term, meaning in TERMS)
    return ("When the reply applies structure, use these words, each with exactly one meaning: " + meanings + ". Use each in a sentence that makes its meaning clear "
            "to someone who has never heard it, never as a bare label or heading, and never swap one for a synonym. The reply is about the person's situation, "
            "not about a framework, so never name the framework or explain the words on their own. Never use an em dash.")
