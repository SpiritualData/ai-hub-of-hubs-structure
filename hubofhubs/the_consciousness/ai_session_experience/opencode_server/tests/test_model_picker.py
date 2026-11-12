"""The picker's tiers follow the hub's TIERS; explicit models come from the chooser; best never runs on another tier's model."""
import json
import http.client

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import command, routes
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.server import OpencodeServer
from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers, tiers
from hubofhubs.the_world.tools.delegated_agent_sessions import providers


def test_the_picker_lists_all_four_tiers_when_the_hub_has_models():
    assert command.offered_tiers() == ("fast", "balanced", "quality", "best")


def test_the_picker_follows_a_changed_tiers_tuple(monkeypatch):
    monkeypatch.setattr(role_tiers, "TIERS", ("fast", "balanced"))
    assert command.offered_tiers() == ("fast", "balanced")


def test_a_tier_with_no_model_is_left_out(monkeypatch):
    real = providers.model_for
    monkeypatch.setattr(providers, "model_for", lambda p, t, folder=None: None if t == "best" else real(p, t, folder))
    assert command.offered_tiers() == ("fast", "balanced", "quality")


def test_best_resolves_to_its_own_arm_not_qualitys():
    chosen = tiers.choose(None, available={"anthropic"})
    assert providers.model_for("anthropic", "best") == chosen["best"]["arm"][1]
    assert providers.model_for("anthropic", "strong") == chosen["quality"]["arm"][1]


def test_explicit_models_are_read_from_the_chooser_and_resolve_to_themselves():
    served = command.offered_models()
    assert served and set(served) >= {providers.model_for("anthropic", t) for t in role_tiers.TIERS}
    assert all(providers.model_for("anthropic", m) == m for m in served)
    assert providers.model_for("anthropic", "not-a-model") is None


def test_the_picker_route_lists_tiers_then_models_and_choosing_a_model_builds_on_it():
    built = []

    class Harness:
        pass
    choices = command.offered_choices()
    bridge = Bridge(lambda folder, tier="": built.append(tier) or Harness(), "/work", tiers=choices, tier="fast")
    listed = routes.handle(bridge, "GET", "/api/model", {}, None)[1]["data"]
    assert [m["id"] for m in listed] == list(choices)
    assert [m["name"] for m in listed][:4] == ["Fast", "Balanced", "Quality", "Best"] and listed[4]["name"] == listed[4]["id"]
    model = command.offered_models()[0]
    routes.handle(bridge, "POST", f"/api/session/{bridge.root}/model", {}, {"model": {"id": model, "providerID": "hub"}})
    assert bridge.tier == model


def test_work_and_server_accept_a_model_and_run_it_as_named():
    from hubofhubs.the_self.assembler.cli import main_session_tier
    model = command.offered_models()[-1]
    assert main_session_tier("", model) == model
    assert main_session_tier("", "best") == "best"


def test_the_real_server_lists_the_picker():
    server = OpencodeServer(Bridge(lambda folder, tier="": None, "/work", tiers=command.offered_choices(), tier="fast"), port=0).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        import base64
        auth = "Basic " + base64.b64encode(f"opencode:{server.token}".encode()).decode()
        conn.request("GET", "/api/model", headers={"Authorization": auth})
        body = json.loads(conn.getresponse().read())
        print("PICKER", [m["id"] for m in body["data"]])
        assert [m["id"] for m in body["data"]] == list(command.offered_choices())
    finally:
        server.stop()
