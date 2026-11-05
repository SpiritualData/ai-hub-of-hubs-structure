"""The interface of WorldKnowing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import List, Optional, Union, runtime_checkable
from esoi import solution
from hubofhubs.the_world.observation import Observation


@solution("the-science", kind="event", entry="search", example="meditation and attention")
@runtime_checkable
class WorldKnowing(typing.Protocol):
    """Looks up what the world says now and returns it as ``Observation`` rows a reader can cite. ``search`` runs one or more queries
    and returns one compact observation (title, link and snippet per hit); ``fetch`` reads one page and returns the passages that bear
    on a focus, or the whole document one part at a time. Neither raises: a failure comes back as an observation of kind ``error``.
    An arm's search need is the ``web-search`` seat, which the consumer chooses."""

    def describe(self) -> str: ...
    def search(self, queries: Union[str, List[str]], *, max_results: Optional[int] = None, fresh: bool = False) -> Observation: ...
    def fetch(self, url: str, *, focus: Optional[str] = None, fresh: bool = False, full: bool = False,
              part: Optional[int] = None) -> Observation: ...
