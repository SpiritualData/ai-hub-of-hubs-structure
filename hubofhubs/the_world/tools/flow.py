"""ToolsComposition."""
import functools
import inspect
from typing import Any, Callable, Mapping, Optional
from esoi import implementation
from esoi.assemble import Lazy
from esoi.entry import call_entry, declared
from hubofhubs.the_self.assembler.resolution import HUB
from hubofhubs.the_world.tools.delegated_agent_sessions.interface import AgentSessions
from hubofhubs.the_world.tools.connected_system_operations.interface import ConnectedOperating
from hubofhubs.the_world.tools.file_editing.interface import FileEditing
from hubofhubs.the_world.tools.file_reading.interface import FileReading
from hubofhubs.the_world.tools.web_search.interface import SearchBackend


@implementation("the-tools", "composition")
class ToolsComposition:
    """Uses the tool of a category through the category's own entry point, refusing a category the Representative's authority does not allow. Web
    Search is needed to build it; the other categories are built on first use, so a request that needs no file, operation or agent never asks for one."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, search: SearchBackend, reader: Lazy[FileReading], files: Lazy[FileEditing], operations: Lazy[ConnectedOperating],
                 sessions: Lazy[AgentSessions]):
        self.parts = {"web-search": search, "read-files": reader, "file-editing": files, "connected-system-operations": operations,
                      "delegated-agent-sessions": sessions}

    def use(self, category: str, request: Any, cancel_check: Optional[Callable[[], bool]] = None, authority: Optional[Mapping[str, Any]] = None) -> Any:
        if category not in self.parts:
            raise ValueError(f"no tool category {category!r}; the categories are {', '.join(self.parts)}")
        owner = str(request.get("owner", "")) if isinstance(request, Mapping) else ""
        scope = (authority or {}).get("data_scope")
        if owner and scope is not None and owner not in scope:      # data scope: the Representative's authority names whose data the AI may read
            raise PermissionError(f"the data of {owner!r} is outside the data scope of this request")
        if isinstance(request, Mapping) and "owner" in request:
            request = {key: value for key, value in request.items() if key != "owner"}
        found = declared(HUB, category)
        call = getattr(self.parts[category], found.entry)
        if cancel_check is not None and "cancel_check" in inspect.signature(call).parameters:      # a worker that can be stopped is given the hook
            call = functools.partial(call, cancel_check=cancel_check)
        return call_entry(call, request)
