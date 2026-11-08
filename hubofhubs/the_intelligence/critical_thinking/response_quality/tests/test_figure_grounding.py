"""Figures are held to the evidence by value."""



def test_a_figure_is_held_by_value_so_a_written_date_matches_an_iso_date_and_a_comma_does_not_matter():
    from hubofhubs.the_intelligence.critical_thinking.response_quality.figure_grounding import strip_unsupported
    evidence = "read 2026-11-06 22:40 UTC; target 1,000 subscribers"
    text = "It was read on 6 November at 22:40. The target is 1000. The rate is 37 percent."
    cut, dropped = strip_unsupported(text, evidence)
    assert dropped == ["37"] and cut == "It was read on 6 November at 22:40. The target is 1000."
