"""Scores the front door on a plain install, a machine with only a logged-in Claude CLI and no vendor key: for an ordinary input, did it end with a real answer or an honest,
actionable message, with no raw error text and with **zero warnings**?

A warning is anything the person would be shown beyond the answer (the result's ``note``) or a step the answer depends on that broke. The test of any message: if it would appear
for most people on a plain install, it is a defect to fix (make the default work) or it is not worth saying, so a case fails on one warning, and the number is the share of cases
passed. Stand-ins (an arm that did the job another arm could not here) are a detail of the result and are not warnings. The cases are scripted by the hand that wrote the rules, so
they show the door holds for these inputs, not for every input."""
RAW = ("Traceback", "Error:", "failed:", "stopped for budget", "hubofhubs[", "pip install", "SearchBackendError", "Exception")


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    answer, expect = str(got["answer"]), case["expect"]
    held = [w.lower() in answer.lower() for w in expect["contains"]]
    answered = bool(answer.strip()) and (any(held) if expect.get("any") else all(held))
    raw = [w for w in RAW if w in answer]
    warnings = (1 if str(got["note"]).strip() else 0) + len(got["broken"])
    ok = answered and not raw and warnings == 0
    note = "" if ok else "; ".join(x for x in ("no real answer: " + answer[:60] if not answered else "", f"raw error text {raw}" if raw else "", f"{warnings} warning(s): {str(got['note'])[:80]}" if warnings else "") if x)
    return dict(ok=ok, got=answer[:60], note=note, answered=answered, warnings=warnings, raw=len(raw))


def aggregate(rows):
    n = max(len(rows), 1)
    return {"plain_install": round(sum(bool(r["ok"]) for r in rows) / n, 3), "answered": f"{sum(bool(r['answered']) for r in rows)}/{len(rows)}",
            "warnings": sum(int(r["warnings"]) for r in rows), "raw_error_text": sum(int(r["raw"]) for r in rows)}
