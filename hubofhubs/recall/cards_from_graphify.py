"""Throwaway stub (validation of records only)."""
from esoi import implementation


@implementation("cards-from-files", "graphify_files")
class GraphifyFiles:
    REQUIRES = ()
    def build(self, root, files, existing): return []
    def changed(self, root, cards): return []
