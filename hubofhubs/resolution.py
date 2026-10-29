"""Name-based resolution over ``esoi.runtime`` scope ``hubofhubs``, done safely.

Config values, rows and environment carry NAMES only. A name is validated here, before ``esoi`` sees it, and accepted only
when it is in ``names()``. Import targets come only from a ``register`` call in consumer code (trusted) and from the hub's
own packaged records and snapshot, whose module must start with ``hubofhubs.`` and lie inside the installed package.
"""
import importlib
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from esoi import runtime

from .config import FORBIDDEN_ENVIRON, SELECT_PREFIX, HubConfig

SCOPE = "hubofhubs"
NAME_PATTERN = "^[a-z0-9][a-z0-9_-]*$"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
PACKAGE_DIR = Path(__file__).resolve().parent
LAYER_LABELS = {"call": "explicit name", "context": "context override", "environment": "selection environ",
                "deployment": "deployment (esoi.toml)", "project": "hub default"}


class HubError(ValueError):
    """A hub resolution error. The message names the solution id, scope, layer, the available names and a remedy."""


@dataclass(frozen=True)
class Choice:
    name: str
    layer: str      # explicit name, consumer selections, selection environ, hub default, ...
    source: str = ""


def check_name(name: Any, what: str = "name") -> str:
    """The name, or ``HubError``. ``:`` and ``.`` (import paths) and anything off the pattern never reach ``esoi``."""
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise HubError(f"{what} {name!r} rejected: a name matches {NAME_PATTERN} (never an import path, so ':' and '.' are "
                       f"refused); remedy: pass one of the names the seat lists with names(solution_id)")
    return name


def environ_of(config: Optional[HubConfig]) -> Dict[str, str]:
    """The environment ``esoi`` is allowed to see: the config field, validated. Never ``os.environ``."""
    raw = dict((config or HubConfig()).selection_environ)
    for key, value in raw.items():
        if key in FORBIDDEN_ENVIRON:
            raise HubError(f"selection_environ may not set {key}: it would point esoi at records the hub did not ship")
        if key.startswith(SELECT_PREFIX) and value:
            check_name(str(value), f"selection_environ {key}")
    return {str(k): str(v) for k, v in raw.items()}


def prepare() -> None:
    """Declare the seats (importing them runs nothing): after this, the scope knows the hub's solution ids."""
    importlib.import_module(f"{SCOPE}.seats")


def known_solution(solution_id: str) -> bool:
    prepare()
    return any(scope == SCOPE and sid == solution_id for scope, sid in runtime.REGISTRY)


def check_solution(solution_id: str) -> str:
    check_name(solution_id, "solution id")
    if not known_solution(solution_id):
        known = sorted(sid for scope, sid in runtime.REGISTRY if scope == SCOPE)
        raise HubError(f"unknown solution {solution_id!r} in scope {SCOPE!r}; available: {', '.join(known) or 'none'}")
    return solution_id


def names(solution_id: str, config: Optional[HubConfig] = None) -> List[str]:
    """Every implementation name that can be chosen for a seat: declared in code, recorded, or in the packaged snapshot."""
    check_solution(solution_id)
    return runtime.names(solution_id, environ=environ_of(config), scope=SCOPE)


def hub_declared(solution_id: str, config: Optional[HubConfig] = None) -> List[str]:
    """Names the hub itself declares for a seat: its records and snapshot, and code in the hub's own modules."""
    project = runtime.project_for(solution_id, environ_of(config), SCOPE)
    found = set()
    if project is not None:
        found |= {n for sid, n in project.paths if sid == solution_id}
        found |= set(project.snapshot.get(solution_id, {}).get("modules", {}))
    entry = runtime.entry_of(solution_id, SCOPE)
    for name, target in (entry.implementations.items() if entry else ()):
        if str(getattr(target, "__module__", "")).startswith(SCOPE + "."):
            found.add(name)
    return sorted(found)


def module_for(solution_id: str, name: str, config: Optional[HubConfig] = None) -> str:
    """The dotted module the hub's own records or snapshot name for an arm ('' when none)."""
    project = runtime.project_for(solution_id, environ_of(config), SCOPE)
    if project is None:
        return ""
    if project.config is not None and (solution_id, name) in project.paths:
        return runtime.module_for(project, project.paths[(solution_id, name)])
    return str(project.snapshot.get(solution_id, {}).get("modules", {}).get(name, ""))


def safe_module(module: str) -> str:
    """A packaged record's module, or ``HubError``: it must start with ``hubofhubs.`` and its ``find_spec`` origin must lie
    inside the installed ``hubofhubs`` directory. Nothing is imported to find out."""
    if not isinstance(module, str) or not module.startswith(SCOPE + ".") or ".." in module:
        raise HubError(f"packaged record module {module!r} rejected: it must start with '{SCOPE}.'")
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        spec = None
    origin = Path(spec.origin).resolve() if spec is not None and spec.origin not in (None, "built-in", "frozen") else None
    if origin is None or PACKAGE_DIR not in origin.parents:
        raise HubError(f"packaged record module {module!r} rejected: its file is not inside the installed {SCOPE} package")
    return module


def choice(solution_id: str, name: Optional[str] = None, config: Optional[HubConfig] = None) -> Choice:
    """Which arm a seat would use now and which layer decided it. Cascade: explicit name, the consumer's selections on the
    config, then the hub default. A name a layer supplies that is unknown is an error, never a fall-through."""
    check_solution(solution_id)
    cfg = config or HubConfig()
    env = environ_of(cfg)
    available = runtime.names(solution_id, environ=env, scope=SCOPE)
    for layer, named in (("explicit name", name or cfg.names.get(solution_id)), ("consumer selections", cfg.selections.get(solution_id))):
        if named:
            check_name(named, f"{layer} for {solution_id!r}")
            if named not in available:
                raise HubError(f"unknown implementation {named!r} for {solution_id!r} in scope {SCOPE!r} (layer: {layer}); "
                               f"available: {', '.join(available) or 'none'}; remedy: use one of them, or register your own "
                               f"under a name you own with register()")
            return Choice(named, layer, "")
    try:
        picked = runtime.choose(solution_id, None, environ=env, scope=SCOPE)
    except runtime.SelectionError as error:
        raise HubError(f"{solution_id!r} in scope {SCOPE!r}: {error}; available: {', '.join(available) or 'none'}; remedy: "
                       f"name one, or provide your own object") from error
    return Choice(picked.name, LAYER_LABELS.get(picked.layer, picked.layer), picked.source)


def load(solution_id: str, picked: str, config: Optional[HubConfig] = None) -> Any:
    """The implementation object for a name. The hub imports a packaged arm's module itself, after the safe-loading check,
    so ``esoi`` never extends ``sys.path`` or imports a module the hub did not vouch for."""
    entry = runtime.entry_of(solution_id, SCOPE)
    if entry is None or picked not in entry.implementations:
        module = module_for(solution_id, picked, config)
        if module:
            importlib.import_module(safe_module(module))
    return runtime.resolve(solution_id, picked, environ=environ_of(config), scope=SCOPE)


def resolve(solution_id: str, name: Optional[str] = None, config: Optional[HubConfig] = None) -> Any:
    """The chosen implementation object of a seat (a class is not instantiated). Reads no environment."""
    return load(solution_id, choice(solution_id, name, config).name, config)
