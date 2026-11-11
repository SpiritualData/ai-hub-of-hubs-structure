"""The standard for standing work: work that repeats unattended is judged by what it changes outside itself.

``STANDING_WORK_STANDARD`` is a prompt constant. A consumer puts it into the brief of every unattended recurring run and shows it to
whoever writes the standing instructions of such a run. Proactivity says when the work is due; this says how the work is written and run.
Standard library only; no model call is made here."""
from esoi import implementation

STANDING_WORK_STANDARD = """STANDING WORK STANDARD. Work that repeats unattended is judged by what it changes outside itself. Whoever writes its standing instructions, and every run of it, holds to these points.
1. COUNT ACTS, NOT REPORTS. Its metric is something the run's own acts move within days (people reached, replies received, things published, defects fixed), with a number to reach each run. A figure only the final outcome moves (revenue, paying customers) is read for direction and is never the run's metric. Measuring an unchanged number again, or producing a summary, plan or draft nobody acts on, is a failed run.
2. ACT WITH WHAT THE RUN HAS. Do the outward act itself with the tools and accounts available, as far as the instructions allow. What the run cannot do goes to one named person as a queue they can clear in minutes: one line per item with the link to open and the exact words to use, most important first.
3. PLAN AROUND THE PEOPLE AS THEY ARE. Name who is involved, what each can be counted on to do, and on which days. Ask a person only for what only a person can do. Access, a sign-in or a first review of wording is asked for once, at setup, with the exact step. A human act that recurs is a scheduled routine of theirs at a set time, never a new ask each run. On a day a person is away the run still does its work.
4. A BLOCKER IS REPORTED ONCE. Ask for what is missing once, then do everything that does not need it. If the earlier runs shown to you report the same blocker, or the metric did not move in the last two, this run changes the way of working instead of repeating it.
5. EVERY RUN IS A TRIAL. Vary one thing at a time (the offer, the wording, the audience, the channel), keep what the responses favor, and record what was learned where the next run starts from it.
6. LEAVE THE NEXT STEP ORDERED. End by ranking what comes next, so the next run or person starts on the most valuable item.
7. SCALE ON FEW TOKENS. Records live in a store that is read in slices, a step repeated by hand becomes a script, bulk work goes to cheaper models, and the strongest model keeps the strategy and the words people read.
8. REVIEW IS SAMPLED AND SCHEDULED. Where a person wants to see outgoing words, they skim a batch at a set time and what they leave unchanged goes out. Approval of every item is used only where they asked for it."""



@implementation("proactivity", "standing_work_standard")
class StandingWorkStandard:
    """The standard as a declared implementation of Proactivity: a text a consumer puts into a run's brief; it decides nothing and calls no model."""
    REQUIRES = ()     # standard library
    text = STANDING_WORK_STANDARD
