"""Shared by the Intuition arms: TF-IDF cosine between a request and each item of a corpus, standard library only. Helper code with no arm of its own."""
import math
from collections import Counter
from typing import Dict, List, Mapping

from hubofhubs.the_body.internal_context.card_store.text_sampling import keywords_from_text


def weights(texts: Mapping[str, str]) -> Dict[str, Dict[str, float]]:
    """The unit-length TF-IDF vector of every item, keyed by item id."""
    counted = {key: Counter(keywords_from_text(text)) for key, text in texts.items()}
    frequency = Counter(word for words in counted.values() for word in words)
    total = max(len(counted), 1)
    vectors: Dict[str, Dict[str, float]] = {}
    for key, words in counted.items():
        raw = {word: n * (math.log((1 + total) / (1 + frequency[word])) + 1.0) for word, n in words.items()}
        norm = math.sqrt(sum(v * v for v in raw.values())) or 1.0
        vectors[key] = {word: v / norm for word, v in raw.items()}
    return vectors


def cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    small, large = (left, right) if len(left) <= len(right) else (right, left)
    return sum(v * large.get(word, 0.0) for word, v in small.items())


def closeness(request: str, texts: Mapping[str, str]) -> Dict[str, float]:
    """The cosine of the request with every item that shares at least one word with it (items sharing none are left out)."""
    vectors = weights({**texts, "": request})
    asked = vectors.pop("")
    scored = {key: cosine(asked, vector) for key, vector in vectors.items()}
    return {key: score for key, score in scored.items() if score > 0.0}


def offered(scores: Mapping[str, float], texts: Mapping[str, str], limit: int, why: Mapping[str, str]) -> List[dict]:
    """The best ``limit`` items by score as the mappings ``offer`` returns: id, text, score and why it came to mind."""
    best = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:max(limit, 0)]
    return [{"id": key, "text": texts[key], "score": round(score, 4), "why": why.get(key, "similar")} for key, score in best]
