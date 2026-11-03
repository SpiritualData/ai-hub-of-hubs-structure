"""The think-critically arm that exists today: hold an answer to the evidence behind it. Every link in the answer must be one the
evidence contains; each link it does not contain is a finding. Pure functions over the existing link detection and matching, no
model call, no network."""
from typing import List, Sequence

from esoi import implementation

from .link_detect import extract_urls
from .link_guard import evidence_urls, normalize_url_for_match


@implementation("think-critically", "evidence_check")
class EvidenceCheck:
    """Findings for an answer: one line per link that the evidence text does not mention."""
    REQUIRES = ()     # pure functions

    def critique(self, answer: str, evidence: str = "") -> Sequence[str]:
        known = evidence_urls(evidence)
        found: List[str] = []
        for url in extract_urls(answer):
            if normalize_url_for_match(url) not in known:
                found.append(f"link not in the evidence: {url}")
        return found
