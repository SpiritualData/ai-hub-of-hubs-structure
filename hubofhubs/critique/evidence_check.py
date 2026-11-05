"""The response-quality arm that exists today: hold an answer to the evidence behind it. Every link in the answer must be one the
evidence contains; each link it does not contain is a finding. Pure functions over the existing link detection and matching, no
model call, no network. It judges one criterion of a quality profile, faithfulness to evidence; the other criteria have no arm yet."""
from typing import Any, List, Optional, Sequence

from esoi import implementation

from .link_detect import extract_urls
from .link_guard import evidence_urls, normalize_url_for_match


@implementation("response-quality", "evidence_check")
class EvidenceCheck:
    """Findings for an answer: one line per link that the evidence text does not mention."""
    REQUIRES = ()     # pure functions

    def judge(self, response: str, evidence: str = "", profile: Optional[Any] = None) -> Sequence[str]:
        """The findings for the criterion this arm judges, faithfulness to evidence, unless the profile does not list it (a profile that has no
        such criterion has nothing for this arm to judge)."""
        if profile is not None and getattr(profile, "criterion", None) and profile.criterion("faithfulness to evidence") is None:
            return []
        return self.critique(response, evidence)

    def critique(self, answer: str, evidence: str = "") -> Sequence[str]:
        known = evidence_urls(evidence)
        found: List[str] = []
        for url in extract_urls(answer):
            if normalize_url_for_match(url) not in known:
                found.append(f"link not in the evidence: {url}")
        return found
