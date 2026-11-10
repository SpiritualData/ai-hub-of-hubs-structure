"""Rebuild ``cases.json`` for Folder View: invented, neutral working folders (a garden, a trip, invoices, a small web shop) built by ``world.py``.

Each case has a goal, the files a competent worker would need (``needed``), the planted traps (dependency, build, cache, secret and backup folders that
share the goal's words, as ``trap_folders``; the risky ones as ``risky_folders``), and, for a goal that names a file inside a risky folder, ``flagged``.
Two strata: ``small`` (a folder of tens of files, budget 6000 characters) and ``corpus`` (hundreds to thousands of files across several ecosystems,
budget 24000). Every case has ``origin: rule`` and says which evidence the needed files can be found by (``evidence``):

  named_path, named_name  the goal gives the path or the file name
  path_words, heading     the goal's words are in the path, or only in the file's headings (opaque file name)
  entity                  an id or quoted string of the goal is in the file's opening
  link                    a named file refers to the needed one
  trail                   earlier runs of the same work used the file
  latest                  the newest of a numbered series
  python_import           a named Python file imports the needed one
  lookalike               a folder named like a build or dependency folder that holds work (no project file beside it)
  risky_unasked           a word match would pick a secrets, key or backup folder
  risky_named             the goal names a file inside a risky folder: it must come back flagged, not shown
  risky_by_content        a folder with an ordinary name holds a key file
  named_folder            the goal (or the context) names a folder, with or without a trailing slash, at depth 1 to 4, or by a bare unique name: the needed
                          files are the folder's orienting files and the few files its words point at, not the whole folder

    python3 evaluation/folder_view/build_cases.py

Standard library only."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from folder_view import world  # noqa: E402

SMALL, CORPUS = 6000, 24000


def doc(title: str, text: str) -> str:
    return f"# {title}\n\n{text}\n"


def case(ident, stratum, evidence, goal, spec, needed, context="", flagged=(), trail=(), heldout=False):
    spec = dict(spec)
    plan = world.plan_of(spec)
    for rel in needed:
        assert rel in plan.files, (ident, rel)
    return dict(id=ident, stratum=stratum, origin="rule", evidence=evidence, goal=goal, context=context, budget=SMALL if stratum == "small" else CORPUS,
                spec=spec, needed=list(needed), trap_folders=sorted(plan.trap_folders), risky_folders=sorted(plan.risky_folders), flagged=list(flagged),
                trail=[dict(path=p, runs=2, changed=False) for p in trail], heldout=heldout)


def notes(count, words="", at="notes", lines=3):
    return dict(count=count, words=words, at=at, lines=lines)


SEED = doc("Seed order for the north bed", "The north bed gets tomatoes, basil and two rows of beans. Order twelve tomato plants and forty bean seeds by the first of March from the Fenwick supplier.")
BUDGET = doc("Autumn gala venue contract", "The Rosewood hall quoted 2400 for the evening and asked for a deposit of 600 by the fifteenth of September.")
INVOICE = "Invoice INV-1042\nAddressed to: Hartley Bakery\nAmount: 318.50\nDue: 2026-03-02\n"
WEEKS = {f"reports/weekly_2026_{n:02d}.md": doc(f"Weekly report {n}", f"Week {n}: stock counted, nothing unusual. Order {n * 3} jars.") for n in range(1, 13)}
WEEK_AGES = {f"reports/weekly_2026_{n:02d}.md": (13 - n) * 7 for n in range(1, 13)}
POLICY = doc("Key rotation policy", "Rotate every service key each ninety days. The owner of a service records the date of each rotation in the register.")
SETTINGS = doc("Settings guide", "Each setting has a default. The timeout is 30 seconds. The retry count is 3. Change a setting only after a review.")
CONTEXT = "Be exact. Quote figures as the files give them."

CASES = [
    case("fv-small-named-path", "small", "named_path", "What does notes/seed_order.md say about the north bed?",
         dict(seed=1, trap_words="seed order north bed", files={"notes/seed_order.md": SEED, "notes/compost.md": doc("Compost", "Turn the heap monthly."), "notes/tools.md": doc("Tools", "Sharpen the spade.")},
              ecosystems=[dict(kind="node", files=12)], notes=notes(8, lines=10)), ["notes/seed_order.md"]),
    case("fv-small-named-name", "small", "named_name", "Summarise seed_order.md for me.",
         dict(seed=2, trap_words="seed order", files={"garden/seed_order.md": SEED, "garden/compost.md": doc("Compost", "Turn the heap monthly.")},
              ecosystems=[dict(kind="python", files=12)], notes=notes(8, lines=10)), ["garden/seed_order.md"]),
    case("fv-small-path-words", "small", "path_words", "What is the plan for the seed order of the north bed?",
         dict(seed=3, trap_words="seed order north bed plan", files={"garden/seed_order_north_bed.md": SEED, "garden/compost_schedule.md": doc("Compost schedule", "Turn the heap monthly."),
                                                                  "garden/tool_list.md": doc("Tool list", "Spade, fork, rake.")},
              ecosystems=[dict(kind="rust", files=12)], notes=notes(8, lines=10)), ["garden/seed_order_north_bed.md"]),
    case("fv-small-heading", "small", "heading", "Find what we decided about the autumn gala venue contract and the deposit.",
         dict(seed=4, trap_words="autumn gala venue contract deposit", files={"notes/entry_0457.md": BUDGET, "notes/entry_0458.md": doc("Menu ideas", "Soup and bread."), "notes/entry_0459.md": doc("Guest list", "Forty guests.")},
              ecosystems=[dict(kind="java", files=12)], notes=notes(8, lines=10)), ["notes/entry_0457.md"]),
    case("fv-small-entity", "small", "entity", "Find invoice INV-1042 and say who it was addressed to.",
         dict(seed=5, trap_words="invoice", files={"billing/export_88.txt": INVOICE, "billing/export_89.txt": "Invoice INV-2001\nAddressed to: Marsh Cafe\n", "billing/export_90.txt": "Invoice INV-2002\nAddressed to: Pike Deli\n"},
              ecosystems=[dict(kind="go", files=12)], notes=notes(8, lines=10)), ["billing/export_88.txt"]),
    case("fv-small-risky-unasked", "small", "risky_unasked", "Summarise our key rotation policy.",
         dict(seed=6, trap_words="key rotation policy", files={"policies/key_rotation.md": POLICY, "policies/holidays.md": doc("Holidays", "Closed on the first of May.")},
              risky=[dict(kind="credentials"), dict(kind="env"), dict(kind="ssh")], notes=notes(8, lines=10)), ["policies/key_rotation.md"]),
    case("fv-small-risky-named", "small", "risky_named", "Check secrets/prod.yaml and docs/settings_guide.md and say which settings need a review.",
         dict(seed=7, trap_words="settings review", files={"docs/settings_guide.md": SETTINGS, "docs/holidays.md": doc("Holidays", "Closed on the first of May.")},
              risky=[dict(kind="secrets")], notes=notes(8, lines=10)), ["docs/settings_guide.md"], flagged=["secrets/prod.yaml"]),
    case("fv-small-lookalike-dist", "small", "lookalike", "Summarise the staff handbook.",
         dict(seed=8, trap_words="staff handbook", files={"dist/staff_handbook.md": doc("Staff handbook", "Start at nine. Lunch is at one. Report faults to the office manager.")},
              ecosystems=[dict(kind="node", at="shopfront", files=10)], notes=notes(8, lines=10)), ["dist/staff_handbook.md"]),
    case("fv-small-lookalike-packages", "small", "lookalike", "Where is the click handler of the ui button?",
         dict(seed=9, trap_words="click handler ui button", files={"package.json": '{"workspaces": ["packages/*"]}\n', "packages/ui/src/button.js": "export function onClick(handler) { return handler; }\n// click handler of the ui button\n",
                                                                "packages/ui/src/label.js": "export const label = 'ok';\n", "packages/core/src/store.js": "export const store = {};\n"},
              ecosystems=[dict(kind="node", at="tools", files=10)], notes=notes(8, lines=10)), ["packages/ui/src/button.js"]),
    case("fv-small-lookalike-vendor", "small", "lookalike", "List the vendor contracts that renew this year.",
         dict(seed=10, trap_words="vendor contracts renew", files={"vendor/contracts_2026.md": doc("Vendor contracts", "The caterer renews in June. The printer renews in October."), "vendor/readme.md": doc("Vendors", "Folder of vendor notes.")},
              ecosystems=[dict(kind="ruby", at="site", files=10)], notes=notes(8, lines=10)), ["vendor/contracts_2026.md"]),
]

BIG = [dict(kind="node", at="projects/shopfront", files=60), dict(kind="python", at="projects/ledger", files=60), dict(kind="rust", at="projects/tally", files=50)]
WIDE = [dict(kind=k, at=f"projects/{k}app", files=70) for k in ("node", "python", "rust", "java", "dotnet", "go", "ruby", "ios")]
RISKS = [dict(kind="credentials"), dict(kind="ssh"), dict(kind="env"), dict(kind="backup", at="ops"), dict(kind="private", at="people")]

CASES += [
    case("fv-corpus-named-path", "corpus", "named_path", "What does notes/garden/seed_order.md say about the north bed?",
         dict(seed=11, trap_words="seed order north bed", files={"notes/garden/seed_order.md": SEED}, ecosystems=BIG, risky=RISKS, notes=notes(900, lines=4)), ["notes/garden/seed_order.md"], context=CONTEXT),
    case("fv-corpus-named-name", "corpus", "named_name", "Summarise staff_rota.md.",
         dict(seed=12, trap_words="staff rota", files={"studio/staff_rota.md": doc("Staff rota", "Ana opens on Monday. Ben closes on Friday.")}, ecosystems=BIG, risky=RISKS, notes=notes(900, lines=4)), ["studio/staff_rota.md"]),
    case("fv-corpus-path-words", "corpus", "path_words", "What is the plan for the seed order of the north bed?",
         dict(seed=13, trap_words="seed order north bed plan", files={"garden/beds/seed_order_north_bed.md": SEED, "garden/beds/compost_schedule.md": doc("Compost schedule", "Monthly.")},
              ecosystems=BIG, risky=RISKS, notes=notes(1200, lines=4)), ["garden/beds/seed_order_north_bed.md"]),
    case("fv-corpus-heading", "corpus", "heading", "What did we decide about the autumn gala venue contract and the deposit?",
         dict(seed=14, trap_words="autumn gala venue contract deposit", files={"events/log/entry_5521.md": BUDGET}, ecosystems=BIG, risky=RISKS, notes=notes(1200, lines=4)), ["events/log/entry_5521.md"]),
    case("fv-corpus-entity", "corpus", "entity", "Find invoice INV-1042 and say who it was addressed to.",
         dict(seed=15, trap_words="invoice", files={"finance/exports/export_0088.txt": INVOICE}, ecosystems=BIG, risky=RISKS, notes=notes(1200, "invoice", lines=4)), ["finance/exports/export_0088.txt"]),
    case("fv-corpus-link", "corpus", "link", "Review docs/overview.md and the details it points to.",
         dict(seed=16, trap_words="payment flow overview", files={"docs/overview.md": doc("Overview", "The shop takes card payments. The steps are in specs/payment_flow.md and the refund rules are in specs/refund_rules.md."),
                                                                "specs/payment_flow.md": doc("Steps of a card sale", "Check the basket, charge the card, send the receipt."),
                                                                "specs/refund_rules.md": doc("Refunds", "Refund within thirty days with the receipt.")},
              ecosystems=BIG, risky=RISKS, notes=notes(1000, "payment flow", lines=4)), ["docs/overview.md", "specs/payment_flow.md", "specs/refund_rules.md"]),
    case("fv-corpus-trail", "corpus", "trail", "Continue the work from last time.",
         dict(seed=17, trap_words="work continue", files={"plan/phase_two.md": doc("Phase two", "Move the stock count to Fridays and train two staff on the till.")}, ecosystems=BIG, risky=RISKS, notes=notes(1000, lines=4)),
         ["plan/phase_two.md"], trail=["plan/phase_two.md"]),
    case("fv-corpus-latest", "corpus", "latest", "Summarise the latest weekly report.",
         dict(seed=18, trap_words="weekly report", files=WEEKS, days_ago=WEEK_AGES, ecosystems=BIG, risky=RISKS, notes=notes(1000, "weekly report", lines=4)), ["reports/weekly_2026_12.md"]),
    case("fv-corpus-python-import", "corpus", "python_import", "Explain how app/net/client.py computes its retry delay.",
         dict(seed=19, trap_words="retry delay", files={"app/net/client.py": "from app.net.backoff import delay\n\n\ndef fetch(attempt):\n    return delay(attempt)\n",
                                                      "app/net/backoff.py": '"""Delay between tries."""\n\n\ndef delay(attempt):\n    return 2 ** attempt\n'},
              ecosystems=BIG, risky=RISKS, notes=notes(800, "retry delay", lines=4)), ["app/net/client.py", "app/net/backoff.py"]),
    case("fv-corpus-lookalike-build", "corpus", "lookalike", "Summarise the packing instructions.",
         dict(seed=20, trap_words="packing instructions", files={"shipping/build/packing_instructions.md": doc("Packing instructions", "Wrap glass twice. Label every box with the order number.")},
              ecosystems=BIG, risky=RISKS, notes=notes(1000, lines=4)), ["shipping/build/packing_instructions.md"]),
    case("fv-corpus-risky-named", "corpus", "risky_named", "Check secrets/prod.yaml and docs/settings_guide.md and say which settings need a review.",
         dict(seed=21, trap_words="settings review", files={"docs/settings_guide.md": SETTINGS}, risky=[dict(kind="secrets")] + RISKS, ecosystems=BIG, notes=notes(1000, lines=4)),
         ["docs/settings_guide.md"], flagged=["secrets/prod.yaml"]),
    case("fv-corpus-risky-unasked", "corpus", "risky_unasked", "What is the backup schedule for the shop database?",
         dict(seed=22, trap_words="backup schedule shop database", files={"ops/runbooks/backup_schedule.md": doc("Backup schedule", "The shop database is saved nightly at two and kept for fourteen days.")},
              ecosystems=BIG, risky=RISKS + [dict(kind="archive")], notes=notes(1000, "backup", lines=4)), ["ops/runbooks/backup_schedule.md"]),
    case("fv-corpus-wide", "corpus", "path_words", "Explain how the order service handles a refund.",
         dict(seed=23, trap_words="order service refund", files={"services/orders/refund_handler.md": doc("Refund handler", "The order service marks the order refunded, then calls the payment provider."),
                                                               "services/orders/shipping.md": doc("Shipping", "Ships within two days.")},
              ecosystems=WIDE, risky=RISKS, notes=notes(1500, "order service", lines=4)), ["services/orders/refund_handler.md"]),
    case("fv-corpus-guards", "corpus", "lookalike", "What are the Q3 targets and how is the deploy script run?",
         dict(seed=24, trap_words="targets deploy script", files={"plans/target/q3_targets.md": doc("Q3 targets", "Raise repeat orders to 30 percent and cut returns to 4 percent."),
                                                                "shop/bin/deploy.sh": "#!/bin/sh\n# deploy script: run ./deploy.sh staging, then ./deploy.sh live\necho deploy\n"},
              ecosystems=BIG, risky=RISKS, notes=notes(1000, "targets", lines=4)), ["plans/target/q3_targets.md", "shop/bin/deploy.sh"]),
    case("fv-corpus-risky-by-content", "corpus", "risky_by_content", "Summarise the deploy guide.",
         dict(seed=25, trap_words="deploy guide notes", files={"docs/deploy_guide.md": doc("Deploy guide", "Deploy on Tuesdays. Ask the lead before a Friday release.")},
              risky=[dict(kind="pem"), dict(kind="service_account")] + RISKS, ecosystems=BIG, notes=notes(1000, "deploy", lines=4)), ["docs/deploy_guide.md"]),
]

MINUTES = {f"meetings/minutes-2026-03-{d:02d}.md": doc(f"Minutes of 2026-03-{d:02d}", f"Present: five. Decided to repaint the hall on day {d}.") for d in (2, 9, 16, 23)}
MIN_AGES = {f"meetings/minutes-2026-03-{d:02d}.md": 30 - d for d in (2, 9, 16, 23)}
HELD = [
    case("fv-held-latest-minutes", "corpus", "latest", "Read the most recent meeting minutes and list what was decided.",
         dict(seed=31, trap_words="meeting minutes decided", files=MINUTES, days_ago=MIN_AGES, ecosystems=BIG, risky=RISKS, notes=notes(900, "meeting minutes", lines=4)), ["meetings/minutes-2026-03-23.md"], heldout=True),
    case("fv-held-quoted-entity", "corpus", "entity", "Find the note that mentions \"Tamsin's rota swap\" and say what was agreed.",
         dict(seed=32, trap_words="rota swap agreed", files={"studio/misc/page_77.md": doc("Page", "Tamsin's rota swap was agreed for the first week of June.")}, ecosystems=BIG, risky=RISKS, notes=notes(900, "rota", lines=4)),
         ["studio/misc/page_77.md"], heldout=True),
    case("fv-held-two-headings", "corpus", "heading", "Compare the allergy policy with the field trip permission rules.",
         dict(seed=33, trap_words="allergy policy field trip permission", files={"school/docs/file_12.md": doc("Allergy policy", "Staff carry two pens. Parents list allergies each term."),
                                                                                 "school/docs/file_31.md": doc("Field trip permission rules", "A signed slip is needed for every trip.")},
              ecosystems=WIDE, risky=RISKS, notes=notes(1500, "policy", lines=4)), ["school/docs/file_12.md", "school/docs/file_31.md"], heldout=True),
    case("fv-held-markdown-link", "corpus", "link", "Read trips/summary.md and follow the budget it links to.",
         dict(seed=34, trap_words="trip budget", files={"trips/summary.md": doc("Trip summary", "Ten days on the coast. The costs are in [the budget](../money/coast_costs_q3.md)."),
                                                      "money/coast_costs_q3.md": doc("Coast costs", "Rooms 900, rail 240, food 400.")}, ecosystems=BIG, risky=RISKS, notes=notes(1000, "trip budget", lines=4)),
         ["trips/summary.md", "money/coast_costs_q3.md"], heldout=True),
    case("fv-held-lookalike-out", "small", "lookalike", "Summarise the results in out/summary.md and the notes in output/.",
         dict(seed=35, trap_words="results summary notes", files={"out/summary.md": doc("Results", "Sales rose 12 percent."), "output/notes.md": doc("Notes", "Two stalls sold out."), "readme.md": doc("Readme", "Market stall records.")},
              ecosystems=[dict(kind="python", at="tool", files=10)], notes=notes(8, lines=10)), ["out/summary.md", "output/notes.md"], heldout=True),
    case("fv-held-env-named", "small", "risky_named", "Check .env and README.md and tell me which variables the app expects.",
         dict(seed=36, trap_words="variables app expects", files={"README.md": doc("App", "The app expects API_TOKEN and NOTE to be set.")}, risky=[dict(kind="env"), dict(kind="aws")], notes=notes(8, lines=10)),
         ["README.md"], flagged=[".env"], heldout=True),
    case("fv-held-other-words", "corpus", "path_words", "Where do we keep the itinerary for the mountain holiday?",
         dict(seed=37, trap_words="itinerary mountain holiday", files={"travel/alps/route_plan.md": doc("Route plan", "Day one: train to the valley. Day two: the high pass.")}, ecosystems=BIG, risky=RISKS, notes=notes(1000, "holiday", lines=4)),
         ["travel/alps/route_plan.md"], heldout=True),
    case("fv-held-recipe-path", "corpus", "path_words", "How long does the sourdough starter need before the first bake?",
         dict(seed=38, trap_words="sourdough starter bake", files={"kitchen/bread/sourdough_starter_guide.md": doc("Starter guide", "Feed twice a day for five days before the first bake.")},
              ecosystems=WIDE, risky=RISKS, notes=notes(1800, "bake", lines=4)), ["kitchen/bread/sourdough_starter_guide.md"], heldout=True),
]
CASES += HELD


def job_folder(base, extra_siblings=True):
    """The files of a named working folder (orienting files, two files the goal's words point at, decoys) and sibling folders that each have the same
    orienting files, so a file every sibling has is evidence."""
    parent = base.rsplit("/", 1)[0] if "/" in base else ""
    files = {
        f"{base}/CLAUDE.md": doc("Context", "This folder holds the job search. Read the goals first, then the tracking notes."),
        f"{base}/GOALS.md": doc("Goals", "Apply to five roles a week and record each one."),
        f"{base}/SYNC.md": doc("Sync", "Last synced on Friday."),
        f"{base}/ml_engineer_leads.md": doc("ML engineer leads", "Three roles listed this week: a retail forecasting team, a map startup and a bank."),
        f"{base}/tracking_notes.md": doc("Tracking notes", "Applied: forecasting team. Waiting: map startup."),
        f"{base}/taxes_2023.md": doc("Taxes 2023", "Filed in April."),
        f"{base}/recipe_ideas.md": doc("Recipe ideas", "Lentil soup."),
        f"{base}/interview_prep_2024.md": doc("Interview prep 2024", "Practice questions for the old role."),
    }
    if extra_siblings:
        for name in ("family", "health", "finance"):
            for fname in ("CLAUDE.md", "GOALS.md", "SYNC.md"):
                files[f"{parent + '/' if parent else ''}{name}/{fname}"] = doc(f"{name} {fname}", f"The {name} area.")
            files[f"{parent + '/' if parent else ''}{name}/misc.md"] = doc("Misc", f"Loose notes about {name}.")
    return files


JOB_NEEDED = ["CLAUDE.md", "GOALS.md", "ml_engineer_leads.md", "tracking_notes.md"]
JOB_GOAL = "Find this week's ML engineer job opportunities and update the job search tracking notes in "
SMALL_ECO = [dict(kind="node", at="projects/shopfront", files=30), dict(kind="python", at="projects/ledger", files=30)]


def folder_case(ident, base, goal, notes_count=800, big=False, heldout=False, context="", risky=(), seed=40, trailing=""):
    spec = dict(seed=seed, trap_words="ml engineer job search tracking", files=job_folder(base), ecosystems=SMALL_ECO, risky=[dict(kind="credentials")] + list(risky),
                notes=notes(notes_count, "job search", lines=4))
    if big:      # hundreds of notes inside the named folder itself
        spec["files"] = dict(spec["files"])
        spec["inner"] = notes(300, "ml engineer job search tracking", at=base, lines=3)
    return case(ident, "corpus", "named_folder", goal, spec, [f"{base}/{n}" for n in JOB_NEEDED], context=context, heldout=heldout)

CASES += [
    folder_case("fv-folder-depth3", "stories/career/job_search", JOB_GOAL + "stories/career/job_search.", seed=41),
    folder_case("fv-folder-depth1-slash", "careers", JOB_GOAL + "careers/.", seed=42),
    folder_case("fv-folder-depth4-slash", "areas/work/search/jobs", JOB_GOAL + "areas/work/search/jobs/ this week.", seed=43, heldout=True),
    folder_case("fv-folder-bare-unique-name", "stories/career/job_search", "Find this week's ML engineer job opportunities and update the tracking notes in the job_search folder.", seed=44),
    folder_case("fv-folder-from-context", "stories/career/job_search", "Find this week's ML engineer job opportunities and update the tracking notes.", seed=45, heldout=True,
                context="Working folder: stories/career/job_search\nEarlier trail: you read stories/career/job_search earlier today and nothing was changed."),
    folder_case("fv-folder-large", "stories/career/job_search", JOB_GOAL + "stories/career/job_search.", seed=46, heldout=True, big=True),
    folder_case("fv-folder-large-depth4", "areas/work/search/jobs", JOB_GOAL + "areas/work/search/jobs/.", seed=47, heldout=True, big=True),
    folder_case("fv-folder-with-secret", "stories/career/job_search", JOB_GOAL + "stories/career/job_search.", seed=48, heldout=True,
                risky=[dict(kind="env", at="stories/career/job_search"), dict(kind="secrets", at="stories/career/job_search")]),
]


def main() -> None:
    (HERE / "cases.json").write_text(json.dumps(CASES, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(CASES)} cases")


if __name__ == "__main__":
    main()
