"""Throwaway stub (validation of records only)."""
from esoi import implementation

from ..seats import ModelCalling


@implementation("cards-from-files", "per_file_symbols")
class PerFileSymbols:
    REQUIRES = ()
    def build(self, root, files, existing): return []
    def changed(self, root, cards): return []


@implementation("cards-from-files", "llm_topic_cards")
class LlmTopicCards:
    """The model is a constructor need typed with the call-a-model seat (hubofhubs.seats.ModelCalling)."""
    REQUIRES = ()
    def __init__(self, provider: ModelCalling): self.provider = provider
    def build(self, root, files, existing): return []
    def changed(self, root, cards): return []
