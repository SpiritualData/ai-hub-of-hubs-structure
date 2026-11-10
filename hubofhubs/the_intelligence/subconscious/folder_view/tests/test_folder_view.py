"""Folder View: the folder judgment (evidence, not names alone), the three arms, and the flagged handling of a risky file the goal names."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))
from hubofhubs.the_intelligence.subconscious.folder_view import judgment  # noqa: E402
from hubofhubs.the_intelligence.subconscious.folder_view.evidence_ranked import EvidenceRanked  # noqa: E402
from hubofhubs.the_intelligence.subconscious.folder_view.interface import FolderViewing  # noqa: E402
from hubofhubs.the_intelligence.subconscious.folder_view.model_pick import ModelPick  # noqa: E402
from hubofhubs.the_intelligence.subconscious.folder_view.ported_baseline import PortedBaseline  # noqa: E402


def make(tmp_path, **files):
    for name, text in files.items():
        path = tmp_path / name.replace("::", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return str(tmp_path)


def left(root):
    return {x.path: x for x in judgment.scan(root).left_out}


def test_every_arm_satisfies_the_interface():
    assert all(isinstance(arm, FolderViewing) for arm in (PortedBaseline(), EvidenceRanked(), ModelPick(complete=lambda s, p: "")))


def test_a_build_folder_is_left_out_only_with_a_project_file_beside_it(tmp_path):
    root = make(tmp_path, **{"app::package.json": "{}", "app::dist::a.js": "x", "notes::dist::handbook.md": "handbook", "notes::readme.md": "r"})
    out = left(root)
    assert "app/dist/" in out and out["app/dist/"].kind == "build" and "notes/dist/" not in out


def test_packages_are_dependencies_beside_a_solution_file_and_source_in_a_monorepo(tmp_path):
    root = make(tmp_path, **{"net::Shop.sln": "s", "net::packages::a::readme.txt": "n", "js::package.json": "{}", "js::packages::ui::button.js": "b"})
    out = left(root)
    assert "net/packages/" in out and "js/packages/" not in out


def test_rust_java_dotnet_go_ruby_and_ios_folders_are_judged_by_their_project_files(tmp_path):
    root = make(tmp_path, **{"r::Cargo.toml": "", "r::target::x.d": "x", "j::pom.xml": "", "j::target::c.txt": "x", "d::App.csproj": "", "d::bin::o.json": "{}",
                             "d::obj::o.json": "{}", "g::go.mod": "", "g::vendor::m.go": "x", "y::Gemfile": "", "y::vendor::b.rb": "x", "i::Podfile": "", "i::Pods::p.swift": "x"})
    assert set(left(root)) == {"r/target/", "j/target/", "d/bin/", "d/obj/", "g/vendor/", "y/vendor/", "i/Pods/"}


def test_environments_and_caches_are_found_by_markers_whatever_their_name(tmp_path):
    root = make(tmp_path, **{"tooling::pyvenv.cfg": "home=x", "tooling::lib::a.py": "x", "stash::CACHEDIR.TAG": "sig", "stash::a.txt": "x",
                             "memo::.gitignore": "*\n", "memo::b.txt": "x", "work::ok.txt": "fine"})
    out = left(root)
    assert set(out) == {"tooling/", "stash/", "memo/"} and out["tooling/"].kind == "dependency" and out["stash/"].kind == "cache"


def test_the_projects_own_gitignore_and_hidden_folders(tmp_path):
    root = make(tmp_path, **{".gitignore": "out_files/\n*.log\n", "out_files::a.txt": "x", ".tool::state.txt": "x", "keep::a.txt": "x"})
    out = left(root)
    assert out["out_files/"].kind == "generated" and out[".tool/"].kind == "hidden" and "keep/" not in out


def test_risky_folders_are_left_out_by_name_and_by_what_they_hold(tmp_path):
    root = make(tmp_path, **{"credentials::keys.txt": "k", "ops::server.pem": "-----BEGIN PRIVATE KEY-----", "ops::notes.txt": "n", "backups::a.sql": "x",
                             "docs::guide.md": "g", ".env": "TOKEN=abcdefghijklmnop1234", "src::credentials.py": "def credentials(): pass"})
    out = left(root)
    assert out["credentials/"].risky and out["ops/"].risky and "server.pem" in out["ops/"].reason and out["backups/"].risky and out[".env"].risky and out[".env"].is_file
    assert "docs/" not in out and "src/" not in out       # a code file named credentials holds none


def test_a_credential_inside_an_ordinary_file_makes_it_risky_when_the_head_is_read(tmp_path):
    root = make(tmp_path, **{"cfg::settings.yaml": "db:\n  password: hunter2hunter2hunter2\n", "cfg::plain.yaml": "mode: fast\n"})
    scanned = judgment.scan(root, inspect=True)
    assert [x.path for x in scanned.left_out if x.is_file] == ["cfg/settings.yaml"] and [f[0] for f in scanned.files] == ["cfg/plain.yaml"]


def test_generated_and_binary_files_are_passed_over_and_counted(tmp_path):
    root = make(tmp_path, **{"package-lock.json": "{}", "a.min.js": "x", "real.md": "text"})
    (tmp_path / "pic.png").write_bytes(b"\0\1")
    scanned = judgment.scan(root, inspect=True)
    assert [f[0] for f in scanned.files] == ["real.md"] and scanned.skipped == {"generated": 2, "binary": 1}


def test_a_file_the_goal_names_inside_a_risky_folder_comes_back_flagged_not_shown(tmp_path):
    root = make(tmp_path, **{"secrets::prod.yaml": "x: 1", "docs::guide.md": "guide"})
    got = EvidenceRanked().choose("Check secrets/prod.yaml and docs/guide.md", "", root, 1000)
    assert [p.path for p in got.picks if p.flagged] == ["secrets/prod.yaml"] and got.paths() == ["docs/guide.md"]
    assert "secrets/" in {x.path for x in got.left_out}


def test_the_evidence_arm_finds_a_file_by_rare_words_in_its_heading_and_leaves_dependencies_out(tmp_path):
    files = {f"notes::n{i}.md": f"# Entry {i}\nbudget plan meeting {i}\n" * 20 for i in range(12)}
    files["notes::odd.md"] = "# Gala contract\nThe Rosewood deposit is 600.\n"
    files.update({"node_modules::pkg::a.js": "gala contract deposit", "package.json": "{}"})
    got = EvidenceRanked().choose("What is the gala contract deposit?", "", make(tmp_path, **files), 500)
    assert got.paths() == ["notes/odd.md"] and "node_modules/" in {x.path for x in got.left_out}


def test_the_latest_of_a_series_and_the_trail_and_links(tmp_path):
    files = {f"reports::week_{n:02d}.md": f"# Weekly report {n}\nstock {n}\n" * 30 for n in range(1, 6)}
    files.update({f"filler::f{i}.md": "other words here\n" * 40 for i in range(10)})
    root = make(tmp_path, **files)
    import os
    for n in range(1, 6):
        os.utime(Path(root) / f"reports/week_{n:02d}.md", (1000 + n, 1000 + n))
    got = EvidenceRanked().choose("Summarise the latest weekly report", "", root, 2000)
    assert got.paths()[0] == "reports/week_05.md" and "reports/week_04.md" not in got.paths()
    got = EvidenceRanked().choose("Continue the work", "", root, 2000, trail=[{"path": "filler/f3.md", "runs": 2, "changed": False}])
    assert got.paths() == ["filler/f3.md"]


def test_the_baseline_keeps_its_old_behaviour_nothing_unasked_for_a_corpus_and_whole_folder_when_it_fits(tmp_path):
    root = make(tmp_path, **{"a.txt": "alpha", "b.txt": "beta", "node_modules::x.js": "x"})
    assert sorted(PortedBaseline().choose("go", "", root, 1000).paths()) == ["a.txt", "b.txt"]
    assert PortedBaseline().choose("go", "", root, 4).paths() == []
    assert PortedBaseline().choose("see b.txt", "", root, 4).paths() == ["b.txt"]


def test_the_model_arm_takes_only_listed_paths_in_its_order_and_falls_back_when_the_call_fails(tmp_path):
    files = {f"d::f{i}.md": f"# Topic {i}\nwords about shipping {i}\n" * 10 for i in range(6)}
    root = make(tmp_path, **files)
    asked = []
    arm = ModelPick(complete=lambda system, prompt: asked.append(prompt) or "d/f3.md\nnot/listed.md\nd/f1.md")
    assert arm.choose("shipping topic", "", root, 100000).paths() == ["d/f3.md", "d/f1.md"] and "d/f0.md" in asked[0]

    def broken(system, prompt):
        raise RuntimeError("down")
    assert ModelPick(complete=broken).choose("shipping topic", "", root, 100000).paths() == EvidenceRanked(bar=0.1, max_picks=30).choose("shipping topic", "", root, 100000).paths()


def test_the_subconscious_hands_back_the_folder_view_when_given_a_folder(tmp_path):
    from hubofhubs.the_intelligence.subconscious.card_recall import CardRecall

    class Held:
        def corpus(self):
            return {}

        def read(self, query, limit=5):
            return []

    class Nothing:
        def offer(self, request, limit=5):
            return []
    root = make(tmp_path, **{"app::package.json": "{}", "app::dist::a.js": "x", "notes.md": "note\n"})
    got = CardRecall(Held(), None, Nothing(), None, None, EvidenceRanked()).prepare("read notes.md", folder=root)
    assert got["folder_view"]["picks"][0]["path"] == "notes.md" and "app/dist/" in {x["path"] for x in got["folder_view"]["left_out"]}
    assert any(step["solution"] == "folder-view" and step["status"] == "done" for step in got["steps"])


def career(tmp_path, count=0, **more):
    files = {"stories::career::job_search::CLAUDE.md": "# Context\nThe job search folder.\n", "stories::career::job_search::GOALS.md": "# Goals\nFive roles a week.\n",
             "stories::career::job_search::ml_engineer_leads.md": "# ML engineer leads\nThree roles.\n", "stories::career::job_search::taxes_2023.md": "# Taxes\nFiled.\n",
             **more}
    for sibling in ("family", "health", "finance"):
        files.update({f"stories::{sibling}::CLAUDE.md": "# C\nx\n", f"stories::{sibling}::GOALS.md": "# G\nx\n", f"stories::{sibling}::misc.md": "# M\nx\n"})
    files.update({f"stories::career::job_search::history::entry_{i}.md": f"# Entry {i}\njob search tracking {i}\n" * 3 for i in range(count)})
    return make(tmp_path, **files)


def test_a_named_folder_shows_its_orienting_files_then_the_files_its_words_point_at(tmp_path):
    root = career(tmp_path, count=40)
    for goal, context in (("Find ML engineer roles in stories/career/job_search.", ""), ("Find ML engineer roles in stories/career/job_search/.", ""),
                          ("Find ML engineer roles in the job_search folder.", ""), ("Find ML engineer roles.", "Working folder: stories/career/job_search")):
        got = EvidenceRanked().choose(goal, context, root, 800)
        assert got.paths()[:3] == ["stories/career/job_search/CLAUDE.md", "stories/career/job_search/GOALS.md", "stories/career/job_search/ml_engineer_leads.md"], goal
        assert not any("history/" in p or "taxes" in p for p in got.paths())


def test_a_named_folder_the_scan_cap_did_not_reach_is_scanned_directly_and_its_secrets_stay_out(tmp_path):
    root = career(tmp_path, **{"stories::career::job_search::.env": "TOKEN=abcdefghijklmnop12345\n", "stories::career::job_search::secrets::prod.yaml": "x: 1\n"})
    got = EvidenceRanked().choose("Update ML engineer roles in stories/career/job_search.", "", root, 2000, file_limit=3)
    assert "stories/career/job_search/CLAUDE.md" in got.paths() and "stories/career/job_search/GOALS.md" in got.paths()
    assert not any(".env" in p or "secrets/" in p for p in got.paths())
    assert {"stories/career/job_search/.env", "stories/career/job_search/secrets/"} <= {x.path for x in got.left_out}


def test_an_env_file_hides_only_itself_while_a_key_file_hides_its_folder(tmp_path):
    root = make(tmp_path, **{"app::.env": "TOKEN=abcdefghijklmnop12345\n", "app::main.py": "x = 1\n", "keys::id_rsa": "k", "keys::notes.txt": "n"})
    out = left(root)
    assert out["app/.env"].is_file and "app/" not in out and out["keys/"].risky
