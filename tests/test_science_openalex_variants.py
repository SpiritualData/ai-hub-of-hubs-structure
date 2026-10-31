"""The OpenAlex variant arms, offline: what each one sends as the search is checked with a recorded response handed in as the transport."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs.science.openalex_keywords import OpenAlexKeywords, OpenAlexKeywordsModel, keyword_query  # noqa: E402
from hubofhubs.science.openalex_semantic import OpenAlexSemantic  # noqa: E402

BODY = json.loads((Path(__file__).resolve().parent / "fixtures" / "openalex_works_search.json").read_text(encoding="utf-8"))
QUESTION = "Could you recommend a paper that explores predicting a reader's native language from eye movement patterns while reading?"


class Response:
    status_code, headers = 200, {}

    def json(self):
        return BODY


class Transport:
    def __init__(self):
        self.calls = []

    def __call__(self, url, *, params, headers, timeout):
        self.calls.append(dict(params))
        return Response()


class Model:
    def __init__(self, reply):
        self.reply, self.asked = reply, []

    def complete(self, prompt, tier=""):
        self.asked.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_the_semantic_arm_sends_the_whole_question_in_the_semantic_parameter_and_no_other_search():
    transport = Transport()
    arm = OpenAlexSemantic(transport=transport, min_interval=0)
    assert arm.min_interval == 0 and OpenAlexSemantic().min_interval == 1.0
    assert arm.search(QUESTION).kind == "query"
    sent = transport.calls[0]
    assert sent["search.semantic"] == QUESTION and "search.title_abstract_keywords" not in sent and "search" not in sent


def test_the_semantic_arm_cuts_a_long_query_to_the_documented_2000_characters():
    transport = Transport()
    OpenAlexSemantic(transport=transport, min_interval=0).search("word " * 1000)
    assert len(transport.calls[0]["search.semantic"]) == 2000


def test_the_keyword_rewrite_drops_question_words_and_filler_and_keeps_at_most_five_terms():
    query = keyword_query(QUESTION)
    assert 0 < len(query.split()) <= 5 and "language" in query.split()
    assert not {"could", "you", "recommend", "paper", "explores"} & set(query.split())
    assert keyword_query("Could you please recommend any papers?") == ""


def test_the_keyword_arm_sends_the_rewrite_in_the_keyword_parameter():
    transport = Transport()
    OpenAlexKeywords(transport=transport, min_interval=0).search(QUESTION)
    assert transport.calls[0]["search.title_abstract_keywords"] == keyword_query(QUESTION)


def test_the_model_arm_sends_what_the_model_wrote_and_falls_back_to_the_rewrite_when_it_fails_or_is_empty():
    for reply, expected in (('"eye movements" native language prediction', "eye movements native language prediction"),
                            ("", keyword_query(QUESTION)), (RuntimeError("down"), keyword_query(QUESTION))):
        transport, model = Transport(), Model(reply)
        OpenAlexKeywordsModel(model, transport=transport, min_interval=0).search(QUESTION)
        assert transport.calls[0]["search.title_abstract_keywords"] == expected and QUESTION in model.asked[0]


def test_the_key_is_an_optional_environ_option_every_openalex_arm_inherits():
    from esoi.assemble import environ_fill, environ_lacking
    from hubofhubs.science.openalex import OpenAlexWorks
    for arm in (OpenAlexWorks, OpenAlexSemantic, OpenAlexKeywords, OpenAlexKeywordsModel):
        assert arm.ENVIRON == {"api_key": "OPENALEX_API_KEY"} and not getattr(arm, "ENVIRON_REQUIRED", ())
        assert environ_fill(arm, {}, {"OPENALEX_API_KEY": "k"}) == {"api_key": "OPENALEX_API_KEY"} and environ_fill(arm, {}, {}) == {}
        assert environ_lacking(arm, {}, {}) == {}
