"""Rebuild cases.json for Resolve a Reference from invented rosters, goal lists and post lists. A case is a phrase and its candidates; ``expect`` is the id of the one candidate the phrase refers
to, or the empty string when the right answer is to abstain. The kinds are a person named by id, name, first name or email; a goal named by its title; and a post (a version of
content) paired with the goal that holds it. Half the cases are the failures this seat exists to end, invented look-alikes: two unrelated goals that share words with the request,
a first name two people have, a name that is a part of another, a request that names two different people's words. Some positives are paraphrases a model can read and the exact arm cannot.

    python3 evaluation/resolve_a_reference/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROSTER = [{"id": "u1", "name": "Ann Lee", "aliases": ["ann.lee@example.org"]}, {"id": "u2", "name": "Joanne Park"}, {"id": "u3", "name": "Bo Chen"}, {"id": "u4", "name": "Dev Rao"}]
TWO_ANNS = ROSTER + [{"id": "u5", "name": "Ann Marie Ortiz"}]
GOALS = [
    {"id": "g1", "name": "Newsletter subscribers import cleanup", "text": "Remove bounced addresses from the imported list."},
    {"id": "g2", "name": "Subscribers survey results", "text": "Summarise what subscribers said in the spring survey."},
    {"id": "g3", "name": "Record podcast episode 12", "text": "Record and edit the episode with the guest."},
    {"id": "g4", "name": "Workshop outline", "text": "Outline the three sessions of the workshop."},
]
POSTS = [
    {"id": "p1", "name": "Post A launch video", "text": "Our launch video shows the studio tour with the founder."},
    {"id": "p2", "name": "Post B launch video", "text": "Our launch video opens on the customer story and ends with the offer."},
    {"id": "p3", "name": "Post C photo thread", "text": "Five photos of the workshop day with a caption each."},
]


def person(name, phrase, expect, roster=ROSTER):
    return {"id": "ref-person-" + name, "kind": "person", "args": {"phrase": phrase, "candidates": roster}, "expect": expect}


def goal(name, phrase, expect, goals=GOALS):
    return {"id": "ref-goal-" + name, "kind": "goal", "args": {"phrase": phrase, "candidates": goals}, "expect": expect}


def post(name, phrase, expect, posts=POSTS):
    return {"id": "ref-post-" + name, "kind": "post", "args": {"phrase": phrase, "candidates": posts}, "expect": expect}


def main():
    cases = [
        person("id", "u3", "u3"), person("whole-name", "Bo Chen", "u3"), person("first-name", "bo", "u3"), person("family-name", "Park", "u2"), person("email-alias", "ann.lee@example.org", "u1"),
        person("unique-first-name", "Ann", "u1"), person("two-same-first-names", "Ann", "", TWO_ANNS), person("whole-name-of-the-longer", "Ann Marie Ortiz", "u5", TWO_ANNS),
        person("part-of-another-name", "Joan", ""), person("unknown-person", "Priya", ""), person("words-of-two-people", "Lee Park", ""), person("a-team-not-a-person", "the content team", ""),
        person("nickname-not-listed", "Annie", ""), person("empty", "", ""), person("filler-only", "the", ""),
        goal("whole-title", "Record podcast episode 12", "g3"), goal("title-in-other-case", "workshop outline", "g4"),
        goal("two-look-alikes", "Send the spring newsletter to subscribers", ""), goal("look-alike-by-one-word", "Record the sales call", ""),
        goal("shared-topic-only", "Survey the workshop attendees", ""), goal("two-share-the-word", "Subscribers", ""), goal("not-on-the-list", "Renew the domain", ""),
        goal("paraphrase", "the goal about tidying the imported email list", "g1"), goal("paraphrase-two", "write up the survey findings for subscribers", "g2"),
        post("by-letter", "Post B", "p2"), post("whole-name", "Post C photo thread", "p3"), post("letter-not-listed", "Post D", ""), post("both-launch-videos", "launch video", ""),
        post("shared-words-other-post", "Our launch photos with a caption", ""),
        post("paraphrase-text", "Our launch video opens on the customer story and ends with the offer.", "p2"), post("paraphrase-photos", "five workshop day photos, each with a caption", "p3"),
        post("unrelated-text", "A reminder that the office is closed on Friday.", ""),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
