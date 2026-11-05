"""Representatives carry what a person declared and never another person's authority; Judgment Calls decides and times its asks."""
from hubofhubs.consciousness.judgment import AskEveryTime, SeverityPolicy
from hubofhubs.consciousness.representatives import DeclaredAuthority


def test_a_declared_person_keeps_their_authority_and_an_undeclared_person_gets_the_least():
    arm = DeclaredAuthority({"ana": {"authority": {"allow": ["web-search", "file-editing"], "data_scope": ["team"]}, "preferences": {"tone": "brief"}}})
    ana = arm.represent("ana")
    assert ana["authority"]["allow"] == ["web-search", "file-editing"] and ana["authority"]["data_scope"] == ["ana", "team"] and ana["preferences"] == {"tone": "brief"}
    bo = arm.represent("bo")
    assert bo["authority"]["allow"] == ["web-search", "the-science"] and bo["authority"]["data_scope"] == ["bo"] and bo["authority"]["person"] == "bo"
    nobody = arm.represent("")
    assert nobody["authority"]["data_scope"] == []


def test_the_severity_policy_proceeds_asks_declines_and_times_the_ask():
    arm = SeverityPolicy({"ana": {"proceed_up_to": "medium", "decline_from": "high"}})
    assert arm.decide({"severity": "none"})["decision"] == "proceed"
    assert arm.decide({"severity": "medium"}, "ana")["decision"] == "proceed"
    assert arm.decide({"severity": "high"}, "ana")["decision"] == "decline"
    medium = arm.decide({"severity": "medium"}, "bo")
    assert medium["decision"] == "ask" and medium["to"] == "human" and medium["timing"]["mode"] == "async" and medium["timing"]["batch"]
    high = arm.decide({"severity": "high"}, "bo")
    assert high["timing"] == {"mode": "sync", "batch": False, "continue": []}
    assert arm.decide({"signal": "escalate_human"}, "bo")["severity"] == "high"


def test_a_flow_that_stopped_is_always_asked_about():
    assert SeverityPolicy().decide({"severity": "none"}, "ana", {"stopped": "budget"})["decision"] == "ask"
    assert AskEveryTime().decide({"severity": "none"}, "ana", {"stopped": "authority"})["decision"] == "ask"
    assert AskEveryTime().decide({"severity": "none"})["decision"] == "proceed"
