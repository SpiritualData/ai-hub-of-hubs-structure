"""Representatives are one identity each, with a person or a character, and never carry another's authority; Judgment Calls decides and times its asks."""
from hubofhubs.the_consciousness.judgment_calls.judgment import AskEveryTime, SeverityPolicy
from hubofhubs.the_consciousness.representatives.representatives import DeclaredAuthority


def test_a_declared_person_keeps_their_authority_and_an_undeclared_person_gets_the_least():
    arm = DeclaredAuthority({"ana": {"authority": {"allow": ["web-search", "file-editing"], "data_scope": ["team"]}, "preferences": {"tone": "brief"}}})
    ana = arm.represent("ana")
    assert ana["authority"]["allow"] == ["web-search", "file-editing"] and ana["authority"]["data_scope"] == ["ana", "team"] and ana["preferences"] == {"tone": "brief"}
    bo = arm.represent("bo")
    assert bo["authority"]["allow"] == ["web-search", "the-science"] and bo["authority"]["data_scope"] == ["bo"] and bo["authority"]["person"] == "bo"
    nobody = arm.represent("")
    assert nobody["authority"]["data_scope"] == []


def test_a_character_with_no_person_is_its_own_identity_and_never_reaches_past_its_asker():
    arm = DeclaredAuthority({"batman": {"character": True, "authority": {"allow": ["web-search"], "data_scope": ["ana", "bo"]}, "preferences": {"voice": "gruff"}},
                             "bailey": {"person": "ana", "authority": {"data_scope": ["team"]}}})
    batman = arm.represent("batman")
    assert batman["representative"] == "batman" and batman["person"] == "" and batman["preferences"] == {"voice": "gruff"}
    assert batman["authority"]["data_scope"] == []                                        # no asker, no one's data
    assert arm.represent("batman", "ana")["authority"]["data_scope"] == ["ana"]            # the asker is the ceiling
    assert arm.represent("batman", "cho")["authority"]["data_scope"] == []
    assert arm.represent("batman", "ana")["authority"]["data_scope"] == ["ana"]
    bailey_for_bo = arm.represent("bailey", "bo")
    assert bailey_for_bo["person"] == "ana" and bailey_for_bo["authority"]["data_scope"] == []   # a rep asked by B never carries A's scope
    assert arm.represent("bailey", "ana")["authority"]["data_scope"] == ["ana", "team"] and arm.represent("bailey")["authority"]["data_scope"] == ["ana", "team"]


def test_the_severity_policy_proceeds_asks_declines_and_times_the_ask():
    arm = SeverityPolicy({"ana": {"proceed_up_to": "medium", "decline_from": "high"}})
    assert arm.decide({"severity": "none"})["decision"] == "proceed"
    assert arm.decide({"severity": "medium"}, "ana")["decision"] == "proceed"
    assert arm.decide({"severity": "high"}, "ana")["decision"] == "decline"
    medium = arm.decide({"severity": "medium"}, "bo")
    assert medium["decision"] == "ask" and medium["to"] == "human" and medium["timing"]["mode"] == "async" and medium["timing"]["batch"]
    high = arm.decide({"severity": "high"}, "bo")
    assert high["timing"] == {"mode": "sync", "batch": False, "continue": []}
    assert arm.decide({"signal": "escalate_human"}, "bo")["severity"] == "medium"      # a signal that names no severity is unchecked, never none


def test_a_flow_that_stopped_is_always_asked_about():
    assert SeverityPolicy().decide({"severity": "none"}, "ana", {"stopped": "budget"})["decision"] == "ask"
    assert AskEveryTime().decide({"severity": "none"}, "ana", {"stopped": "authority"})["decision"] == "ask"
    assert AskEveryTime().decide({"severity": "none"})["decision"] == "proceed"


def test_the_consciousness_flow_carries_a_declared_persons_authority():
    from hubofhubs.the_consciousness.flow import ConsciousnessComposition
    arm = DeclaredAuthority({"ana": {"authority": {"allow": ["web-search", "file-editing"], "data_scope": ["team"]}, "preferences": {"tone": "brief"}}})
    class Priorities:
        def prioritize(self, person: str = "", **kwargs):
            return []
    flow = ConsciousnessComposition(arm, Priorities(), None, None, None, None)
    carried = flow.represent("ana")["representative"]
    assert carried["authority"]["allow"] == ["web-search", "file-editing"] and carried["authority"]["data_scope"] == ["ana", "team"] and carried["preferences"] == {"tone": "brief"}
