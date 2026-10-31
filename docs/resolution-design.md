# Resolution design: name-based parts, done safely, for mass adoption

**Status 2026-10-30:** the generic parts of this design (name validation, safe loading, the cascade, needs from typed parameters, the
`uses_solution_ids` check, build order, startup failure) now live in the esoi library as `esoi.assemble`; `hubofhubs.resolution`
binds one `Assembler` to scope `hubofhubs`. Where this page says `needs.py`, `graph.py` or `assembly.py`, read `esoi.assemble`.
What stays here is the seats, the arms, the registry and the scorer.

Descriptive wording in the ESOI records stays the owner's: any new prose reads "unconfirmed: for the owner to confirm".
The hub (package, import name and distribution name `hubofhubs`; the name was unclaimed on PyPI when checked on 2026-10-29, and the
GitHub repository keeps the name `ai-hub-of-hubs-structure`) holds real executing code: seats as
Protocols, arms in per-library extras, and the assembly that wires them. Its core is the standard library plus `esoi`.
It gives a consumer what the earlier name-keyed framework (`repo-utils`) gave: pass a name from configuration or a row
and get the implementation that holds it, loaded lazily, installed only if needed, without that framework's risks.

## 1. Model

**Seats are Protocols.** Each seat is a Protocol class decorated `@solution(id)`; seats are Protocol classes only, so
importing one runs nothing. An implementation is a class or function decorated `@implementation`.

**Needs come from constructor parameters.** No new record field. An implementation's constructor parameters typed with
a seat Protocol ARE its needs. The existing `uses_solution_ids` column is generalised: a check (an `esoi records sync`
style command or a hub test) writes it from those parameters and validates it on every run.

**`hubofhubs.assemble(config, provided={...})`** builds objects in dependency order. For each seat a consumer-provided
object wins; otherwise the hub default (the cascade below) is built. A cycle or an unmet need fails at startup with the
chain named (`a -> b -> a`; `a needs search-backend: no arm, not provided`). Resolution happens inside `assemble`, then
the result is frozen (no resolving at call time, so no locks are needed).

**External systems** (web search, an integration, a paper index) are seats with an `external` tag. The justification is
the solution's own approach and out_of_scope wording, not a new field. A seat with no hub arm is consumer-provided: its
`selected` is empty and the usage note says so. A default-install arm may use an external seat only if that seat has a
default arm or is consumer-provided.

**Zero configuration.** `hubofhubs.assemble()` with no arguments builds every seat whose selected arm needs nothing from the
consumer and puts the rest in `result.pending`, one line per seat saying what to pass (`arms`, `options` or `provided`); it raises
only for an unknown name or a cycle. A consumer names only what differs: `assemble(arms={seat: arm}, options={seat: {...}},
provided={seat: object})`. Passing an `AssemblyConfig` stays the strict form. The mechanic is `esoi.assemble.Assembler.assemble_defaults`;
the hub only supplies its scope. Today the seats with a selected arm are `card-store`, `choose-a-model-tier`, `read-registry-freshness`, `score-hub-connections` and `model-call`
(the last needs the `call-a-model` seat, which stays pending until its arm is named); every other seat is reported as pending until
a metric selects an arm or the consumer provides an object. `assemble(environ=mapping)` fills the options an arm declares in its
`ENVIRON` attribute from that mapping (`esoi.assemble`).

**Cascade (QAR's, unchanged).** Explicit name, then the consumer's selections, then the hub default (`selected` in the
records, or the packaged snapshot in an installed copy). A name that a layer supplies but is unknown is an error, never a
fall-through. Consumers register into scope `hubofhubs` under names they own; the hub wrapper refuses `replace` of a
hub-declared name. Selections live on the consumer's assemble object, never process-wide, so two consumers in one
process do not see each other.

**Reason line.** Startup logs one line per seat: `search-backend -> searxng (layer: consumer selections, package
version, config hash)`; the version is the arm's package version, the hash covers its config.

**Kept from repo-utils.** (1) A consumer manifest listing the seats it uses (the assemble config); it drives the extras
to install and the "every need resolves" check. (2) An automated dependency check: the third-party imports of each arm
module must equal its declared extra, and the extras list is generated from it. (3) One generic `hubofhubs call
<solution-id> --name x --args '{...}'`, limited to declared interfaces.

## 2. Safe loading

**Names only.** Config values, database rows and environment carry NAMES, validated against
`^[a-z0-9][a-z0-9_-]*$` and accepted only if in `names()`. Anything containing `:` or `.` is rejected before `esoi`
sees it. Import targets come only from (a) a `register` call in consumer code (trusted) and (b) the hub's own packaged
records and snapshot, where the module must start with `hubofhubs.` and its file must lie inside the
installed `hubofhubs` directory (`Assembler.safe_module` decides that from the file's position, importing nothing).

**Plain `esoi.runtime` reads more than the environment**: `ESOI_ROOT` and `ESOI_SNAPSHOT`, the working directory, an upward
walk for `esoi.toml`, swallowed load errors, `sys.path` appends. The hub does not use it for assembly. `esoi.assemble.Assembler`
takes an explicit records folder or the packaged snapshot (the hub passes none: it uses its snapshot), does no upward walk,
consults no deployment table, `override()` or process environment, raises load errors and leaves `sys.path` alone. Its
`selection_environ` field is the only environment `esoi` is given. The tests are the library's (`tests/test_assemble.py`:
the hostile parent `esoi.toml`, `sys.path` unchanged, hostile names, look-alike modules).

## 3. Risks found in repo-utils and the hub answer

Sources: the repo-utils sections and GAP entries of the evolvable-structure skill, plus the code they cite.

| # | Risk or oddity | Hub answer |
|---|---|---|
| R1 | Filesystem walk at import: wrappers attached per folder, so import cost and behaviour depend on what is on disk | Registry comes from declarations and record rows. Importing the package reads no directory. Records are read on first resolve, once. Test: inert import (section 4) |
| R2 | Git-root dependence: lookups depend on where the repository is | The hub's own code never asks where the repo is. Plain `esoi.runtime` reads cwd, `ESOI_ROOT`/`ESOI_SNAPSHOT` and walks up for `esoi.toml`; `esoi.assemble.Assembler` does not (section 2). The hub reads its packaged snapshot, and `tests/test_no_environment.py` asserts the snapshot equals the records; the library's `test_r2_r4_a_hostile_parent_esoi_toml_is_never_read_and_sys_path_is_unchanged` resolves from a directory holding a hostile `esoi.toml` |
| R3 | First match by folder name wins silently | Keys are scope + solution id + name. `esoi.runtime.add` raises on a second declaration with a different object, but `register(..., replace=True)` can replace, so `Assembler.register` refuses `replace` of any name the package declares, and a `runtime.register(..., replace=True)` made behind it is refused when the arm is loaded; consumers use their own names. Tests: `tests/test_resolution.py`, and the library's `test_r3_nothing_routes_around_shadowing` |
| R4 | `sys.modules` wrapper magic changes identity, `isinstance` and tracebacks | No `sys.modules` edits. Resolve returns the real object |
| R5 | Env-var reload switch with truthiness trap (`"0"` turns it on) | The hub reads no environment itself: settings are config fields. `esoi.runtime` does read `ESOI_SELECT_*`, `ESOI_ROOT` and `ESOI_SNAPSHOT`, so passing `environ` from a config field (default `{}`) is the control, and a test proves an environment variable does not change a result. A scan for `os.environ` in the hub is secondary |
| R6 | Install-time bootstrap in `setup.py` writes files and installs packages | `pyproject.toml` only, declarative. Test: the build runs no hub code |
| R7 | Textual rename replaces substrings | Renames are record edits plus a checked symbol rename. `esoi check` fails a dangling id. No alias after a rename (section 4) |
| R8 | Documented but not implemented behaviour | Each documented behaviour has a named test. Metric selection is build time (`esoi select`), and the docs say so |
| R9 | Registry forked by copying | One registry (`esoi.runtime`), consumed as a dependency, never copied |
| R10 | Name and metadata drift | One test: package name, import name, changelog heading and `esoi.toml` package agree |
| R11 | Dependency pruning by text scan misses dynamic names | Extras per arm, generated from a per-arm import check (section 1). A missing extra at run time raises an error naming the extra |
| R12 | Swallowed errors | The hub adds no retry or swallow wrappers, and its own errors name the solution, scope and layer. `esoi.assemble` raises `AssemblyError` for an unreadable snapshot or records, an arm that cannot be imported and a default that cannot be chosen (library tests `test_r12_errors_are_raised_not_swallowed`) |
| R13 | Everything public is a CLI command; install runs arbitrary files | Public API is an explicit `__all__`. CLI is a fixed table: `call` limited to declared interfaces, `check`. No command installs or executes arbitrary files |
| R14 | Kind decided by path | Kind is declared: a Protocol for the seat, a class or function for the arm. Conformance is checked once, in tests |
| R15 | Version from an env var, private pinned zips | Version is a literal in `pyproject.toml`; dependencies pinned there |
| R16 | Old Python matrix | Supported versions stated and run in CI |
| R17 | Template leftovers and stubs go uncaught | Parse and import check over every module; `esoi check` fails a record whose file declares nothing under that name; any cache has a test that a second identical call hits |
| R18 | Experiment configuration not reproducible from a file | Selection is data (config fields); the reason line is logged with every run |

## 4. Adoption checklist

| Item | Requirement | Proof |
|---|---|---|
| Default install | `pip install hubofhubs` brings `esoi` only; every arm is an extra | `tests/test_default_install.py`: dependencies equal `["esoi"]` |
| Import boundary | Every import in the package is stdlib, the package or `esoi` (an allowlist) | `tests/test_import_boundary.py` (present) |
| Inert import | No code, network, thread or file write at import | `tests/test_import_is_inert.py`: subprocess with sockets blocked, read-only directory, empty environment |
| Reproducible resolution | Same inputs, same result, in any directory, any registration order | `tests/test_resolution_order.py`, plus the hostile-directory and vendored-copy tests (R2) |
| Clear errors | Every error names solution id, scope, layer, available names and a remedy | `tests/test_errors.py` |
| Safe loading | Section 2 rules | The library's `tests/test_assemble.py` (config value `os:system`, snapshot module `os`, filepath `../x.py`, a look-alike module earlier on `sys.path`, all rejected); the hub's `tests/test_safe_loading.py` checks that every module its snapshot names is its own file |
| Quickstart | A second consumer with no Quest content: register a toy part, assemble, print the reason | `docs/quickstart.md` run as `tests/test_quickstart.py` |
| Types | `py.typed`, hints on the public API, a Protocol per seat | type-check of the package in CI |
| Public API | Solution ids and implementation names ARE the public API. The `(solution id, name)` pairs are pinned in a stored list; removal without a deprecated alias is a breaking change. Deprecated names warn and name the replacement for at least one minor release | `tests/test_public_api.py` |
| Thread safety | Resolve inside `assemble` at startup, then freeze | test: two threads calling an assembled object while nothing resolves |
| Isolation | Two consumers with different selections in one process do not affect each other | `tests/test_isolation.py` |
| PyPI order | `esoi` is released first, then the hub; PyPI rejects direct-URL dependencies | `tests/test_metadata.py` |
| Hygiene | No real names, emails, ids or machine paths | the hub's hygiene scan before every commit |

Dropped as theatre for now: a "copied from" notice scan, a hardcoded-path test (the hygiene scan covers it), an
`isinstance` performance scan, a no-telemetry scan (the blocked-socket import test covers it), SBOM and signing before a
PyPI release exists, and a three-OS matrix before snapshot paths exist.

## 5. Plan

Each step ends with its tests and one local commit by explicit path; nothing is pushed. Status on 2026-10-29.

1. **Baseline by implementation id**: `scripts/baseline.py` writes `docs/baseline.json` (executed-line share per
   implementation id, not per module path); `--check` fails on a drop. Done.
2. **Import-boundary allowlist test**: `tests/test_import_boundary.py`. Done.
3. **Rename to `hubofhubs`, no alias**: package, import name, distribution, esoi scope, docs, tests, records. Done in the hub;
   the consumer's imports of the hub change in its own repository (a later task, owned by its agent).
4. **No environment reads**, plus the hostile-directory and vendored-copy tests (R2, R5). Done: `tests/test_no_environment.py`.
   The hole that was left with `esoi` (a hostile `esoi.toml` in a parent folder found by its upward walk) is closed by
   `esoi.assemble.Assembler`, which never walks up.
5. **Resolve wrapper and `assemble`**: cascade, refusal of `replace` on hub names, reason line, name validation, safe
   loading. Done: `hubofhubs.resolve`, `register`, `assemble`; `tests/test_resolution.py`, `tests/test_safe_loading.py` and `test_example_consumer.py` (a second consumer and a leak detector); the generic tests are the library's `test_assemble.py`.
6. **Needs from typed constructor parameters**, the `uses_solution_ids` check and the graph checks (no cycles, every need
   resolves, external-seat rule). Done: `hubofhubs.seats`, `esoi.assemble`, `scripts/sync_uses.py --check`,
   `tests/test_graph.py`; the default card store `LocalCardStore` is the first executing arm. Eight seats have no natural
   Protocol yet and stay "no arm yet".
7. **Per-seat import check, then the port move.** Moving ports "as they are" is impossible: 65 of the consumer's 106
   adapter modules import its core. For each seat, compute its imports first; move the Protocol and neutral helpers only;
   everything else arrives through `assemble`. The consumer keeps re-exports at the old paths. The seats to move are
   measured in the consumer before the move. Done for the first pass (2026-10-29): `hubofhubs.ports.scope`, `.model` and `.context`
   (usage scoping, `ModelProvider` and the step-hint helpers, the context assembler, conversation store and vector store Protocols) moved
   verbatim from the consumer, comments made consumer-free; the consumer's modules re-export them. The progress events, channels,
   guidance and value objects stay in the consumer (they carry its vocabulary or fields).
   Second pass (2026-10-29), the web-search seat: `hubofhubs.websearch` holds the `search-backend` arms (SearXNG, JSON search APIs
   described as data, Gemini grounding, a provider's own search), the cache, the daily limiter, SSRF-guarded fetching and
   extraction, and the research adapter; `hubofhubs.ports.search` and `.retrieval` hold the neutral values. The convention for
   moving a seat, to follow for the next one: (1) compute each module's imports and move a module only if it is generic;
   (2) the hub reads no environment, so a function that read one takes the mapping and the names of its settings as arguments
   (`SelectionKeys`), and the consumer's one-call constructor from its own settings stays in the consumer; (3) the hub resolves
   by name through its own seat and takes an optional `resolver` callable, so a consumer that owns its selection passes its own
   and the hub never imports it; (4) third-party libraries are imported inside functions and listed as per-library extras
   (`tests/test_import_boundary.py` enforces both); (5) the consumer keeps a thin module at the old path: a re-export, or a
   subclass that declares the consumer's own `@implementation` row and restores any environment default; (6) the hub records
   get ids, paths and `unconfirmed: for the owner to confirm.` text, and `selected` stays empty until a metric result chooses.
   Not moved: the Tavily retrieval adapter (a duplicate of the `tavily` arm plus the research adapter; a deletion candidate in
   the consumer), and the consumer's one-call research constructor. `WebResearchAdapter` is library code, not yet a seat arm:
   `know-the-world` has no Protocol, which is a decision for the seat's owner.
8. **Docs**: quickstart (done: `docs/quickstart.md`, run by `tests/test_quickstart.py`); versioning, releasing and
   changelog remain.

Not done and still owed from section 4: `tests/test_inert_import.py`, `test_errors.py` as a named file, `test_public_api.py`
(the pinned `(solution id, name)` list), `test_isolation.py` as a named file (covered in `test_resolution.py`), the
per-arm extras and the generated-extras import check, the `hubofhubs call` command, `py.typed` and the CI type-check.
