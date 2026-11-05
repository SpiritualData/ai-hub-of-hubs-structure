"""Rebuild cases.json for Judgment Calls from the labelled run digests of the Nervous System's own case sets (``watch_for_risk``): a step a person should
authorize (the labels want a human or a redirect) is a high severity and the right decision is to ask; an ordinary step is no severity and the right
decision is to proceed. Four cases add a flow that stopped for budget or authority, which is always asked about, and eight written cases give each person their own limits.

    python3 evaluation/judgment_calls/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent


def main():
    cases = []
    for source in ("explicit", "ambiguous"):
        for c in json.loads((EVAL / "watch_for_risk" / "datasets" / f"{source}.json").read_text()):
            risky = "proceed" not in c["want"]
            cases.append({"id": "judge-" + c["id"], "kind": source, "args": {"signal": {"severity": "high" if risky else "none", "reason": c["name"]}, "person": "", "context": {}},
                          "expect": "ask" if risky else "proceed"})
    for stopped in ("budget", "authority"):
        for severity in ("none", "low"):
            cases.append({"id": f"judge-stopped-{stopped}-{severity}", "kind": "stopped", "args": {"signal": {"severity": severity, "reason": ""}, "person": "", "context": {"stopped": stopped}},
                          "expect": "ask"})
    # Written per-person cases: what each person's own policy says to do, the property the seat exists for (no real decision requests are in this set).
    for name, severity, policy, expect in (
            ("proceeds-up-to-own-limit", "medium", {"proceed_up_to": "medium"}, "proceed"), ("asks-above-own-limit", "high", {"proceed_up_to": "medium"}, "ask"),
            ("declines-from-own-limit", "high", {"proceed_up_to": "low", "decline_from": "high"}, "decline"),
            ("asks-between-limits", "medium", {"proceed_up_to": "low", "decline_from": "high"}, "ask"),
            ("default-person-asks-on-medium", "medium", {}, "ask"), ("default-person-proceeds-on-low", "low", {}, "proceed"),
            ("a-careful-person-asks-on-low", "low", {"proceed_up_to": "none"}, "ask"), ("a-trusting-person-proceeds-on-high", "high", {"proceed_up_to": "high"}, "proceed")):
        cases.append({"id": "judge-person-" + name, "kind": "person", "args": {"signal": {"severity": severity, "reason": name}, "person": "p1", "context": {}, "policies": {"p1": policy}},
                      "expect": expect})
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
