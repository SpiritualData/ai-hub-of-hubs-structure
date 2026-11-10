"""LocalFileContextComposition."""
from typing import Any, List, Mapping, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_intelligence.subconscious.local_file_context.cards_from_files.interface import CardsFromFiles
from hubofhubs.the_intelligence.subconscious.local_file_context.folder_view.interface import FolderViewing
from hubofhubs.the_self.steps import done, listing, take


@implementation("local-file-context", "composition")
class LocalFileContextComposition:
    """A working folder as context: Folder View chooses the files a piece of work is shown first and the folders left out, and Cards From Files proposes the
    cards the folder's files need. Each part is measured on its own; this arm only calls them."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, folder_view: Lazy[FolderViewing], builder: Lazy[CardsFromFiles]):
        self.folder_view, self.builder = folder_view, builder

    def prepare(self, goal: str, root: str, budget_chars: int = 100000) -> Mapping[str, Any]:
        viewed = take(self.folder_view, "folder-view", goal=goal, context="", root=root, budget_chars=budget_chars)
        return {"folder_view": done(viewed), "steps": listing([viewed])}

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]:
        return list(done(take(self.builder, "cards-from-files", root=root, files=files, existing=existing)) or [])
