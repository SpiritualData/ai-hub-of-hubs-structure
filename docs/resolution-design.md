# Resolution design: name-based parts, done safely, for mass adoption

Status: design, not built. Anything marked **UNSURE** is a judgement the owner should confirm before it is built.
Descriptive wording in the ESOI records stays the owner's: where this document proposes record fields or
wording, they are proposals ("unconfirmed: for Joshua to confirm").

The hub (package `hubofhubs`, today `ai_hub_of_hubs`) should give a consumer what the earlier name-keyed definition
framework (`repo-utils`) gave its users: pass a name from configuration or a database row and get whatever
implementation currently holds it, loaded lazily, shipped only if needed. It should do this without the risks that
framework carried. The mechanism is not new code in the hub: it is the ESOI runtime registry (`esoi.runtime`:
`@solution`, `@implementation`, `register`, `resolve`, scopes) used under the scope `hubofhubs`, plus the records
that already list every implementation with its file. This document says how to use it, what to add, and what to
test.

## 1. What repo-utils gave, and the equivalent here

| What it gave | How (repo-utils) | Equivalent in ESOI and `hubofhubs` |
|---|---|---|
| Name lookup | `import_definition("name")` walks the repo for a folder called `name` and returns the object | `resolve("solution-id", "name")` in scope `hubofhubs`; the solution id and implementation name are rows in `esoi/solutions.csv` and `esoi/implementations.csv`, not folders found by walking |
| Name from config or a row | A caller passes any string | Same: `resolve(solution_id, name)`; the name comes from a config field, never from a hub-read environment variable (section 3 rules) |
| Lazy loading | `ReloadWrapper` placed in `sys.modules`; real code loads on first call | An implementation is imported only when chosen, from the `filepath` of its record; `core` never imports an adapter at import time |
| Pruned packaging | `list_dependencies` scans import lines; `enable_installing_dependencies` writes temporary `__init__.py` files during `setup.py` | Per-library extras: `pip install hubofhubs[mem0]` brings only that arm's dependencies. The records say which arm needs which extra. No source scanning, no build-time file creation |
| Scaffolding | `define <name>` writes a folder, `<name>.py`, `test_<name>.py`; path decides function or class | `esoi` scaffolding for a new solution or implementation (record row plus file plus test); the kind is a typed Protocol, not a path convention |
| Same registry for dev and prod | One walk of the tree in both; `RELOAD_DEFs` env var reloads in dev | One cascade in both: explicit name, context override, consumer config, hub default (section 3). Dev reload is a test helper (`forget` then re-declare), not a production switch |
| Swap by changing a string | Rename or move a folder, callers unchanged | Change the name in config; record `selected` changes only through `esoi select` on the seat's metric |
| Tool commands as definitions, CLI via `fire.Fire` | Every public definition becomes a subcommand | Not copied (risk row R13). A small explicit `hubofhubs` CLI with a fixed command list |

## 2. Risks and oddities found in repo-utils, and what the hub does about each

Sources: the repo-utils sections and GAP entries of the evolvable-structure skill (`sources/code_repos.md`), read in
full, plus behaviour of the code they cite. "GAP" means that entry's wording.

| # | Risk or oddity | Evidence | Hub answer |
|---|---|---|---|
| R1 | Filesystem walk at import: `__init__.py` calls `os.walk` over the package and attaches a wrapper per folder, so import cost grows with tree size and depends on what is on disk | Definition discovery (`import_space_defs`, `os.walk`) | Registry is built from declarations and record rows, not from disk. Importing `hubofhubs` reads no directory and no file beyond the package itself. Records are read on first `resolve`, once |
| R2 | Git-root dependence: lookups walk from the repository root (`find_definition` over `src_root`, `get_repository_path`), so an installed copy, a zip or a vendored copy behaves differently from a checkout | Name-based lookup; Bootstrap block | Resolution never asks where the repo is. An installed package carries a generated snapshot of its records (`esoi select --snapshot`), read from package data. Tested against a built wheel in a clean directory with no `.git` |
| R3 | First match wins by folder name anywhere in the tree: two definitions with the same name silently resolve to whichever `os.walk` meets first, which changes when a folder is added | `find_definition` returns the first folder named `def_name` | Ids are namespaced (`scope` + solution id + implementation name). A second declaration under the same key with a different object raises `SelectionError` at declaration time (this is `esoi.runtime.add` behaviour). A consumer replaces on purpose with `register(..., replace=True)`, which is recorded and visible |
| R4 | `sys.modules` wrapper magic: a lazy wrapper is installed under the folder name so `from repo_utils import define` works; the wrapper then replaces itself with the raw function, so identity, `isinstance`, pickling, tracebacks and type checkers all see something different from what was written | Definition discovery (`load_definition_once`) | No `sys.modules` edits. `resolve` returns the real object. Typed Protocols give static checkers the contract |
| R5 | Env-var reload switch: `RELOAD_DEFs` read at import; any non-empty string (including "0") turns it on, and a library reading the process environment surprises embedders | `os.environ.get("RELOAD_DEFs", False)`; same truthiness trap in the case study (`bool(os.getenv("SHOULD_BE_VERIFIED", 0))`, GAP list) | The hub reads no environment at all. Every setting is a field on a config object the consumer builds (it may fill the field from its own environment). Test: a scan that fails on `os.environ`, `os.getenv`, `environ` in `hubofhubs/` (section 5, step 2). **UNSURE:** `esoi.runtime` itself reads `ESOI_SELECT_*` and `ESOI_ROOT`; the hub must pass `environ={}` (the function accepts a mapping) so the library layer is also inert. Needs a test that proves it |
| R6 | Install-time bootstrap in `setup.py`: `impstall('rc-repo-utils')` installs a package during setup, writes `__init__.py` files, then deletes them; an interrupted build leaves the tree dirty, and building a wheel runs network installs | Bootstrap block in `setup.py` | `pyproject.toml` only, declarative, no `setup.py`. Build runs no hub code. Test: the build backend is a plain one and a build in a network-less sandbox succeeds |
| R7 | Textual rename that replaces substrings: `text.replace(def_name, target_name)` also rewrites any word containing the name | Renaming (`rename_def`), noted in its own GAP-adjacent caveat | Renames are record edits plus a checked symbol rename, never a text replace. `esoi check` fails on a dangling id. A rename keeps the old name as a recorded deprecated alias for one minor release (section 4, deprecation) |
| R8 | Documented but not implemented: README promises a `version` parameter and metric-based selection that the code lacks | GAP: documented but not implemented | Every documented behaviour has a test named in the docs. The metric-based choice exists as `esoi select` over records, and the doc says it is a build-time action, not a call-time one |
| R9 | Registry forked: the case-study package copied `repo_utils/__init__.py` and changed `ReloadWrapper.__call__`, so two registries drifted | Case study, Repo utils usage (`ReloadWrapper` diff) | One registry (`esoi.runtime`), consumed as a dependency, never copied. A vendored-code NOTICE rule (section 4) covers the rest |
| R10 | Name and metadata drift: changelog says an older name, `__meta__` another, unused sample module left in | GAP: drift in names and template leftovers; easyinfo placeholders | Name, version and changelog are checked by one test: package name in `pyproject.toml`, the import name, the changelog heading and the `esoi.toml` package must agree |
| R11 | Dependency pruning by text scan misses dynamic names: a name read from config or a database is invisible to an import scan, so the pruner can drop code the running system needs (or keep too much) | `list_dependencies` follows `from <package> ... import` lines only | Pruning is by declared extras per arm, not by scanning. A name chosen at run time that needs a missing extra raises an error that names the extra to install (section 4, error messages) |
| R12 | Swallowed errors: `ReloadWrapper.__call__` retries on `TypeError`, hiding genuine type errors in the called function | Case study, Repo utils usage: "retries on `TypeError`" | No retry wrappers. Errors propagate with the name, scope and layer |
| R13 | Everything public is a CLI command and an import target, so adding a helper silently widens the surface; `install_def` runs `install.sh`, `requirements.txt`, then `install.py`, i.e. arbitrary code from the tree | Project tooling; CLI | Public API is an explicit `__all__` list. CLI commands are listed in one table. No command installs or executes arbitrary files |
| R14 | Kind decided by path (`/objects/` in the path makes a class) | Scaffolding (`define`) | Kind is declared: a Protocol for the interface, a class or function for the implementation. A test checks the implementation satisfies the Protocol's members (once, at registration or in tests, not per call) |
| R15 | Tests and metadata depend on the environment: version from an env var (`WHL_VERSION`), private requirements pinning a zip artifact by file name | Case study `__meta__.py`; CI workflows | Version is a literal in `pyproject.toml`. Dependencies are pinned in `pyproject.toml` or a lock file, not private zips |
| R16 | Old Python matrix (3.6, 3.9 in the optional workflow) and Windows only in a matrix, never run path logic checks | Optional CI workflows | Supported versions are stated and run in CI (section 4) |
| R17 | Template leftovers: the case study has code that does not parse or is an empty stub inside the registry's own consumer (converters, metrics, cache key, scoring), and nothing in the framework caught it | GAP: checked against the code (all five entries) | A parse check and import check over every module in `hubofhubs` in CI; `esoi check` fails an implementation record whose file declares nothing under that name; an empty stub fails the "implementation is declared" check. The cache-key mismatch lesson becomes a rule: any cache has a test that a second identical call hits |
| R18 | Experiment configuration is Python constants and database rows with no loader, so which implementation ran is not reproducible from a file | GAP: last entry | Selection is data: a config field or an `esoi.toml` selection table. Resolution returns a reason (section 3) that can be logged with every run |

## 3. Resolution, `needs` and `requires`

### 3.1 Resolution order and the printed reason

One deterministic cascade, innermost wins. A name that no layer supplies falls to the next layer; a name that a layer
supplies but is unknown is an error, never a fall-through.

1. Explicit config override: the consumer passes `selections={"search-backend": "searxng"}` (a field on the config
   object the consumer builds; the hub reads no environment).
2. Consumer scope: an implementation the consumer registered for that solution id in its own scope
   (`register(..., scope="<consumer>")`).
3. Hub scope: an implementation declared in scope `hubofhubs`.
4. Default: the solution's `selected` in the records (or the snapshot in an installed copy).

`resolve_with_reason(solution_id, name=None, ...)` returns the implementation plus a `Choice(name, layer, source)`
(this shape already exists as `esoi.runtime.Choice`). The reason prints as one line:
`search-backend -> searxng (layer: config override, scope: hubofhubs)`. Consumers log it at startup. Unknown names
raise an error that lists the layer that supplied the bad name and the available names.

**UNSURE:** `esoi.runtime` orders per call, context, environment, deployment, project. The hub's four layers map onto it
if the consumer's `selections` are passed as the per-call name and the consumer's registered implementations are
resolved before the hub's. Whether the consumer layer (2) needs a small wrapper in the hub or a change in `esoi`
(which is Joshua's personal repository, so a proposal to him) should be decided in step 3 of the plan.

### 3.2 `needs`

A solution declares what it needs by name, never by import. Proposed new column on `esoi/solutions.csv` (and the
same on implementations when one arm needs more than the seat):

- `needs`: semicolon-separated names of other solutions, e.g. `card-store;quest-api;search-backend;database`. Each is a
  solution id resolved at run time from the consumer's scope first, then the hub's own default.

Example record cell (proposed wording, unconfirmed: for Joshua to confirm): `needs = card-store;search-backend`.

The existing `uses_solution_ids` column on implementations (used by the Quest AI Runner records) already records
solution-level use. The design reuses it: `needs` on a solution is the contract; `uses_solution_ids` on an
implementation is what that implementation actually calls. A check requires `uses_solution_ids` of an implementation to
be a subset of `needs` of its solution plus ids it declares itself.

**UNSURE:** whether `needs` should be a new column or the existing `uses_solution_ids` generalised to the solution
level. A new column is clearer to read but is a record-template change, which `esoi` governs (Joshua's repo). Open a
proposal to Joshua; until it is accepted, record the intent in `usage_notes` and enforce in the hub's own test.

### 3.3 `requires`

`requires` marks a system the solution's scope genuinely depends on and cannot work without: an integration, a search
backend, a paper index. It is not a code import. It is justified in the record in one sentence
("requires: paper-index, because the seat's job is to cite papers"). A solution with `requires` can declare
`consumer-provided` or a default arm. Rules:

- Every `requires` has a justification sentence in the record.
- A `requires` that has no default arm in the default install is declared `consumer-provided`.
- A solution with neither `needs` nor `requires` is fully self-contained in the default install.

### 3.4 Checks (all in the hub's own tests; first four also as an `esoi`-level check proposal)

1. **No cycles.** Build the directed graph of solution ids from `needs` and `uses_solution_ids`; fail on any cycle and print
   it. Test: `tests/test_needs_graph.py` with a deliberately cyclic fixture that must fail.
2. **Every need resolves.** For each `needs` name, either a hub default arm exists in the default install or the
   record says `consumer-provided`. Test: `tests/test_needs_resolve.py`, run with the default install only.
3. **Hub never imports a consumer.** A static scan of `hubofhubs/` imports against a deny list of every known consumer
   package name, plus a generic test: import `hubofhubs` with a fresh interpreter whose `sys.path` holds only the hub and
   `esoi`, and assert every submodule imports. Consumers are late-bound by name only.
4. **Libraries are injected, never imported.** An open-source library that wants to use the hub receives parts by name:
   it exposes a parameter (`card_store="card-store"` or a registered object), and the hub-side resolves it. The library
   does not `import hubofhubs`. Test: a second-consumer fixture (section 4, quickstart) that is a stdlib-only toy
   library using a name from config, and a scan that fails if a library fixture contains an import of `hubofhubs`.
5. **Leak scan.** The hub's own tests fail if any Quest content (identifiers, prompts, product names) appears in `hubofhubs/`
   or its records. See step 4.

## 4. Mass-adoption readiness checklist

Each item names the file or test that proves it. "Planned" means the file does not exist yet.

| Item | Requirement | Proof (file or test) |
|---|---|---|
| Small default install | `pip install hubofhubs` installs stdlib plus `esoi` only. Every arm's dependency is a per-library extra; imports are lazy | `pyproject.toml` `[project.optional-dependencies]` (planned); `tests/test_default_install.py` creates a clean virtual environment and imports every non-arm module; a second test asserts the dependency list equals `["esoi"]` |
| Types | `py.typed` marker, full hints on the public API, Protocols for each seat | `hubofhubs/py.typed` (planned); a type-check run over the public API in CI (scoped to the package, not the consumer) |
| Versioning | Semantic versioning, one public API list (`__all__`), a stated deprecation policy: a deprecated name works for at least one minor release and emits a `DeprecationWarning` that names the replacement | `docs/versioning.md` (planned); `tests/test_public_api.py` compares `__all__` to a stored list so a removal is deliberate |
| Changelog | Keep-a-changelog format, one entry per user-visible change, heading matches the package name and version | `CHANGELOG.md` (planned); `tests/test_metadata.py` (R10) |
| Python and OS matrix | State supported Python versions (currently `>=3.11` in `pyproject.toml`) and run Linux, macOS and Windows in CI. No hard-coded paths; all file access through `pathlib` and package data (`importlib.resources`) | `.github/workflows/test.yml` matrix (planned); `tests/test_no_hardcoded_paths.py` scans for `/home`, drive letters and `os.sep` literals |
| Reproducible resolution | Same inputs give the same implementation, in any directory, on any OS, any dict order | `tests/test_resolution_order.py`: each layer in turn wins; an unknown name errors; running twice and with shuffled registration order gives the same result |
| Clear errors | Every resolution error says which solution id, which scope, which layer supplied the name, the available names, and what to register or install: `search-backend: no implementation named 'tavily' (scope hubofhubs, layer: config override). Available: searxng, serper. To add one: register("search-backend", "tavily", obj) or pip install hubofhubs[tavily]` | `tests/test_errors.py` asserts the text contains id, scope, layer and a remedy |
| Security: execution | No code execution at import, no install-time bootstrap, no network at import, no file writes at import | `tests/test_import_is_inert.py`: import in a subprocess with sockets blocked, a read-only working directory, and an empty environment; assert no output, no thread started, no file touched |
| Security: data loading | Registry data is loaded with the standard `csv` module as data only; never `eval`, `exec`, `pickle`, or `yaml.load` unsafe. A dotted path in a record is imported only if it begins with a package the record's scope owns | `tests/test_safe_loading.py` with a hostile record row (a dotted path to `os.system`) that must be rejected. **UNSURE:** the allowed-prefix rule needs thought for consumer-registered `"module:Attr"` strings; a consumer registering its own string is trusted code, a record from the hub is not |
| Supply chain | `esoi` pinned by git commit until released; dependency review in CI (a dependency-review action or `pip-audit`); an SBOM generated per release; signed releases (sigstore attestations) when published to PyPI | `pyproject.toml` pin; `.github/workflows/audit.yml` (planned); `release/` checklist in `docs/releasing.md` (planned) |
| No telemetry | The hub never sends usage data, never phones home, never checks for updates | `tests/test_import_is_inert.py` (sockets blocked) plus a scan of `hubofhubs/` for network modules outside the arm adapters |
| Licence and NOTICE | Apache-2.0. Any vendored or adapted code keeps its licence text and gets a `NOTICE` line; the repo-utils lineage is not copied (R9) | `LICENSE`, `NOTICE` (planned); `tests/test_notice.py` fails if a file carries a "copied from" marker with no NOTICE entry |
| Docs and quickstart | A quickstart for a second consumer with no Quest content: install, register one toy part by name, resolve it from a config dict, print the reason. Runs as a test | `docs/quickstart.md` (planned); `tests/test_quickstart.py` executes the quickstart's code block |
| Performance budget | `import hubofhubs` under a stated budget (**UNSURE** of the number; measure first, then fix it, e.g. 50 ms over importing `esoi`); first `resolve` reads records once and caches; later resolves are dictionary lookups; no `runtime_checkable` `isinstance` on hot paths (check conformance once at registration or in tests); resolve once at startup and keep the object | `tests/test_perf_budget.py` (import time, 1000 resolves under a bound, and a scan that fails on `isinstance(` with a Protocol in hot modules) |
| PyPI note | PyPI rejects direct-URL dependencies. Until `esoi` is released on PyPI, `hubofhubs` cannot be uploaded; consumers install from the git URL (as in the README). Releasing `esoi` comes first, then `hubofhubs` | `docs/releasing.md` states the order; `tests/test_metadata.py` fails a build for PyPI if any dependency is a URL |
| Hygiene | No real names, emails, ids or machine paths, in files or history | `esoi hygiene` over the repo; run before every commit |

## 5. Step-0 implementation plan

The order below follows the reviewer's recommendation. Each step ends with its tests and one local commit by explicit
path. No push.

0. **Record the executed-line-share baseline first.** Before any change, run the scoped tests with coverage over
   `ai_hub_of_hubs/` and record the share of lines executed, per module, in `docs/baseline.md`. Later steps must not
   lower it. Test: the recorded figure is regenerated by one script and compared in CI (`tests/test_baseline.py` fails
   on a drop larger than a stated tolerance). **UNSURE:** whether to use `coverage` as a dev-only dependency; it stays
   out of the default install.
1. **Rename to `hubofhubs` with no alias.** Package folder, `pyproject.toml` `packages`, `esoi.toml` `package`, imports, docs,
   README install lines. Do not keep `ai_hub_of_hubs` importable. The consumer's binding (Quest AI Runner) must change
   its imports in its own repository at the same time; coordinate, because another agent is working there. Tests:
   `tests/test_rename.py` asserts `import ai_hub_of_hubs` fails and `import hubofhubs` works; `esoi check` passes.
2. **The hub reads no environment; settings are config fields.** Replace every environment read in the hub with a field on
   a frozen config dataclass the consumer builds. Test: a scan fails on `os.environ`, `os.getenv`, `environ` under
   `hubofhubs/` (comments excluded); `tests/test_import_is_inert.py` runs with an empty environment. Also pass
   `environ={}` to `esoi.runtime` calls (R5).
3. **`resolve` and `register` over `esoi` scope `hubofhubs`.** A thin module `hubofhubs/resolve.py` modelled on the way
   Quest AI Runner's `core/resolve.py` wraps `esoi.runtime` (explicit name or overrides dictionary, `register`, a
   `names` list, `chosen_name`), plus `resolve_with_reason` (3.1). Tests: `tests/test_resolution_order.py`,
   `tests/test_errors.py`, a collision test (R3), a lazy-import test (an arm whose module raises on import is not
   imported until chosen).
4. **Leak scan in the hub's own tests.** `tests/test_no_consumer_content.py`: a deny list of consumer package names and
   Quest-specific terms, applied to code, records and docs; plus the import-with-only-hub-and-esoi test (3.4, item 3).
   Run `esoi hygiene` as a test.
5. **Move core and adapters ports as they are.** Move the port definitions (Protocols) and the adapters from the
   consumer into the hub unchanged, one seat at a time, each with its existing tests, so behaviour is unchanged. Each
   adapter's third-party dependency becomes a per-library extra. Tests: the consumer's existing tests for that seat still
   pass against the moved code (run only those files); `tests/test_default_install.py`.
6. **Split `runtime_settings` and `jsonl_ledger`.** Separate the settings object (config fields only, no environment)
   from the ledger writer (file I/O, behind a Protocol, injected). Tests: settings construct with no I/O; ledger tested
   with a temporary directory, including Windows path handling.
7. **Rewrite stale docs.** `README.md`, `CLAUDE.md`, `docs/connect-a-hub.md` and the records' usage notes still describe the
   scorer-only design and the old package name. Rewrite to the resolution design, add `docs/quickstart.md`,
   `docs/versioning.md`, `docs/releasing.md`, `CHANGELOG.md`. Tests: `tests/test_quickstart.py`, `tests/test_metadata.py`,
   and `esoi check`.
8. **Add `needs` and `requires` to the records** only after the owner accepts the field proposal (3.2, 3.3); then the
   graph checks (3.4 items 1 and 2). This is last because it changes the record template, which the owner approves.

Everything in this document is a design. No code in the hub or in Quest AI Runner was changed to write it.
