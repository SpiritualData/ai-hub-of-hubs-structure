"""``assemble(config, provided=...)``: build the seats a consumer uses, in dependency order, once, at startup.

For each seat a consumer-provided object wins; otherwise the hub default (the cascade) is built. A cycle or an unmet need
fails here, naming the chain. Resolution happens inside ``assemble`` and the result is frozen: nothing resolves at call time,
so no lock is needed. Selections live on the config the consumer hands in, never in a process-wide table.
"""
import hashlib
import importlib.metadata
import inspect
import json
import logging
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from esoi import runtime

from . import resolution
from .config import HubConfig
from .needs import builder_of, needs_of, protocol_of
from .resolution import SCOPE, HubError

log = logging.getLogger("hubofhubs")


def package_version(target: Any) -> str:
    top = str(getattr(target, "__module__", None) or type(target).__module__).split(".")[0]
    try:
        return importlib.metadata.version(top)
    except importlib.metadata.PackageNotFoundError:
        return "unversioned"


def config_hash(options: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(options, sort_keys=True, default=str).encode()).hexdigest()[:8]


class Assembly:
    """The built objects of one consumer, frozen. ``assembly[solution_id]`` is the object; ``reasons`` has one line per seat."""

    def __init__(self, config: HubConfig, objects: Mapping[str, Any], reasons: Mapping[str, str]):
        self.config = config
        self.objects = MappingProxyType(dict(objects))
        self.reason_by_seat = MappingProxyType(dict(reasons))

    @property
    def reasons(self) -> Tuple[str, ...]:
        return tuple(self.reason_by_seat.values())

    def seats(self) -> List[str]:
        return list(self.objects)

    def __getitem__(self, solution_id: str) -> Any:
        try:
            return self.objects[solution_id]
        except KeyError:
            raise HubError(f"{solution_id!r} was not assembled; assembled seats: {', '.join(self.objects) or 'none'}; "
                           "remedy: list it in HubConfig.seats or provide it") from None

    def __contains__(self, solution_id: str) -> bool:
        return solution_id in self.objects

    def get(self, solution_id: str, default: Any = None) -> Any:
        return self.objects.get(solution_id, default)

    def choice(self, solution_id: str, name: Optional[str] = None) -> resolution.Choice:
        return resolution.choice(solution_id, name, self.config)

    def resolve(self, solution_id: str, name: Optional[str] = None) -> Any:
        """The implementation object (not built) under this consumer's selections."""
        return resolution.resolve(solution_id, name, self.config)


def check_provided(solution_id: str, obj: Any) -> None:
    resolution.check_solution(solution_id)
    protocol = protocol_of(solution_id)
    if protocol is not None and getattr(protocol, "_is_runtime_protocol", False) and not isinstance(obj, protocol):
        raise HubError(f"the object provided for {solution_id!r} does not satisfy {protocol.__name__}")


def seats_with_a_default(config: HubConfig) -> List[str]:
    found = []
    for scope, sid in sorted(runtime.REGISTRY):
        if scope != SCOPE:
            continue
        try:
            resolution.choice(sid, None, config)
        except HubError:
            continue
        found.append(sid)
    return found


def assemble(config: Optional[HubConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
    cfg = config or HubConfig()
    given = dict(provided or {})
    resolution.environ_of(cfg)
    resolution.prepare()
    for sid, obj in given.items():
        check_provided(sid, obj)
    objects: Dict[str, Any] = {}
    reasons: Dict[str, str] = {}

    def need_error(chain: List[Tuple[str, str]], sid: str) -> HubError:
        trail = " -> ".join(s for s, _ in chain + [(sid, "")])
        if chain:
            parent, arm = chain[-1]
            return HubError(f"{parent} ({arm}) needs {sid}: no arm, not provided (chain: {trail}); remedy: pass "
                            f"provided={{{sid!r}: ...}} or register an arm for it")
        return HubError(f"{sid}: no arm, not provided; remedy: pass provided={{{sid!r}: ...}} or register an arm for it")

    def build(sid: str, chain: List[Tuple[str, str]]) -> Any:
        if sid in objects:
            return objects[sid]
        if sid in [s for s, _ in chain]:
            ring = [s for s, _ in chain]
            raise HubError("dependency cycle: " + " -> ".join(ring[ring.index(sid):] + [sid]))
        if sid in given:
            objects[sid] = given[sid]
            reasons[sid] = (f"{sid} -> {type(given[sid]).__name__} (layer: consumer provided, package version "
                            f"{package_version(given[sid])}, config hash {config_hash({})})")
            return objects[sid]
        explicit = bool(cfg.names.get(sid) or cfg.selections.get(sid))
        try:
            picked = resolution.choice(sid, None, cfg)
        except HubError:
            if explicit:
                raise
            raise need_error(chain, sid) from None
        target = resolution.load(sid, picked.name, cfg)
        options = dict(cfg.options.get(sid, {}))
        kwargs = {param: build(need, chain + [(sid, picked.name)]) for param, need in needs_of(target).items()}
        if inspect.isclass(target) or inspect.isfunction(target):   # a class or factory is built; anything else is an instance
            built = builder_of(target)
            params = inspect.signature(built).parameters if built is not None else {}
            extra = [k for k in options if k not in params or k in kwargs]
            if extra:
                raise HubError(f"{sid} ({picked.name}) has no option(s) {', '.join(extra)}; its parameters: "
                               f"{', '.join(p for p in params if p != 'self' and p not in kwargs) or 'none'}")
            kwargs.update(options)
            objects[sid] = target(**kwargs)
        else:
            objects[sid] = target
        reasons[sid] = (f"{sid} -> {picked.name} (layer: {picked.layer}, package version {package_version(target)}, "
                        f"config hash {config_hash(options)})")
        return objects[sid]

    for sid in (list(cfg.seats) or sorted(set(given) | set(seats_with_a_default(cfg)))):
        resolution.check_solution(sid)
        build(sid, [])
    for line in reasons.values():
        log.info(line)
    return Assembly(cfg, objects, reasons)
