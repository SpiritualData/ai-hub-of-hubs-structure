"""The one place that says which kinds of case make up the single score of ``context_assembler``.

``MIX`` names the case sources (files of ``datasets/``) and how many cases of each are in the set, so a source's share is its count over
the sum: the 323 public medical queries (``nfcorpus``, the whole official test split), the 300 title or abstract-sentence queries over the
paper sample (``papers``) and the 300 paraphrased queries over the same sample (``paraphrase``), about a third each. The proportion is by
size of what was available and carries no claim about how often real queries are short topic questions, titles or paraphrases; when a
sample of real queries exists, calibrate the counts here and nowhere else (a source gives its first ``count`` cases).
"""
MIX = {"nfcorpus": 323, "papers": 300, "paraphrase": 300}
