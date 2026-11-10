"""AiSessionExperienceComposition."""
from typing import Any, Callable, Iterable, Mapping, Sequence, TextIO
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_consciousness.ai_session_experience.frontend_interface.interface import FrontendInterfacing
from hubofhubs.the_consciousness.ai_session_experience.structure_in_view.interface import StructureViewing
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.interface import Conversing
from hubofhubs.the_self.steps import listing, skipped, take
from hubofhubs.the_self.steps import done


@implementation("ai-session-experience", "composition")
class AiSessionExperienceComposition:
    """One session, three views. Structure In View says which solutions the AI is working on and what each sub-agent does there, collapsed until a person
    asks for more; Frontend Interface carries the run and that structure as plain data for a separate frontend; Terminal Experience draws the structure as
    lines and is the interactive entry. The events and controls they share are the contract of this solution."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, terminal: Lazy[Conversing], frontend: Lazy[FrontendInterfacing], structure: Lazy[StructureViewing]):
        self.terminal, self.frontend, self.structure = terminal, frontend, structure

    def present(self, events: Sequence[Any], records: Any = None, expanded: Sequence[str] = (), controls: Sequence[Any] = (), width: int = 100) -> Mapping[str, Any]:
        seen = take(self.structure, "structure-in-view", events=events, records=records, expanded=expanded)
        view = done(seen)
        sent = take(self.frontend, "frontend-interface", events=events, controls=controls, structure=view)
        lines = (take(self.terminal, "terminal-session", method="structure_lines", view=view, width=width) if view is not None
                 else skipped("terminal-session", "no structure was produced to draw"))
        return {"structure": view, "frontend": done(sent), "terminal": done(lines), "steps": listing([seen, sent, lines])}

    def converse(self, front_door: Callable[[str], Any], lines: Iterable[str], out: TextIO, viewer_id: str = "", prompt: str = "> ") -> int:
        """The interactive entry: Terminal Experience reads what the person types, sends each line through ``front_door`` and draws the work and any question."""
        held = take(self.terminal, "terminal-session", front_door=front_door, lines=lines, out=out, viewer_id=viewer_id, prompt=prompt)
        return done(held)
