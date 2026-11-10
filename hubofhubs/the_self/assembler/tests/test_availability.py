"""When the selected arm of a solution cannot run here, the best-measured arm that can stands in; the order is the measured one, an arm the caller named stays."""
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from evaluation.plain_install import fake_claude  # noqa: E402
from hubofhubs.the_self.assembler import availability  # noqa: E402
from hubofhubs.the_self.assembler.resolution import HUB  # noqa: E402

import sync_arm_order  # noqa: E402


def standing(environ, arms=None):
    chosen, found = availability.stand_ins(HUB, environ, arms)
    return chosen, {row.solution: row for row in found}


def test_with_only_the_claude_cli_the_search_and_the_model_caller_are_covered(tmp_path):
    chosen, found = standing({"PATH": str(fake_claude.install(tmp_path))})
    assert chosen["web-search"] == "claude_login" and found["web-search"].selected == "gemini"
    assert chosen["vendor-model-caller"] == "claude_cli" and found["vendor-model-caller"].selected == "multi_provider"
    assert all(row.reason for row in found.values())


def test_with_nothing_available_the_selected_arm_stays_and_nothing_is_replaced():
    chosen, found = standing({})
    assert "web-search" not in chosen and "web-search" not in found


def test_an_arm_the_caller_named_is_kept(tmp_path):
    chosen, found = standing({"PATH": str(fake_claude.install(tmp_path))}, {"web-search": "gemini"})
    assert chosen["web-search"] == "gemini" and "web-search" not in found


def test_the_standing_in_follows_the_measured_order_not_a_preference(tmp_path):
    order = availability.arm_order()["web-search"]
    chosen, _found = standing({"PATH": str(fake_claude.install(tmp_path)), "SERPER_API_KEY": "k"})
    ready = [name for name in order if name in ("claude_login", "serper")]
    if importlib.util.find_spec("httpx") is None:
        ready = ["claude_login"]
    assert chosen["web-search"] == ready[0]


def test_the_arm_order_file_names_real_arms_and_matches_the_leaderboard():
    order = availability.arm_order()
    assert order and all(set(arms) <= set(HUB.names(solution)) for solution, arms in order.items())
    assert json.loads(sync_arm_order.TARGET.read_text()) == sync_arm_order.order(), "run python3 scripts/sync_arm_order.py"
