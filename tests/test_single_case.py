"""The top-level single case runs offline with a fake model-call: the same script a consumer runs live once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import single_case  # noqa: E402


class FakeModel:
    def __init__(self, reply):
        self.reply, self.asked = reply, []

    def complete(self, prompt, tier=""):
        self.asked.append((prompt, tier))
        return self.reply

    def usage(self):
        return {"tokens_in": 20, "tokens_out": 2}


def test_a_reply_with_the_digit_passes_with_reasons_and_cost():
    model = FakeModel("4")
    record = single_case.run(model)
    assert model.asked == [(single_case.QUESTION, "cheap")]
    assert single_case.passed(record)
    assert record["arm"] == ["anthropic", "claude-haiku-5-5"]
    assert record["list_cost_usd"] > 0
    assert sorted(r.split(" -> ")[0] for r in record["reasons"]) == ["choose-a-model-tier", "model-call"]


def test_a_wrong_reply_fails():
    assert not single_case.passed(single_case.run(FakeModel("five")))
