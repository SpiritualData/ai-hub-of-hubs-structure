# Resolution design: name-based parts, done safely, for mass adoption

Descriptive wording in the ESOI records stays the owner's: any new prose reads "unconfirmed: for Payal to confirm".
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
records and snapshot, where the module must start with `hubofhubs.` and its `find_spec` origin must lie inside the
installed `hubofhubs` directory.

**`esoi` reads more than the environment**: `ESOI_ROOT` and `ESOI_SNAPSHOT`, the working directory, an upward walk for
`esoi.toml`, swallowed load errors, `sys.path` appends. Hub-side fixes: the wrapper always passes `environ` from a config
field (`selection_environ`, default `{}`); the hub's own `esoi.toml` has no `[selection]` table (a test).

**Proposal for the `esoi` owner (not applied here; `esoi` is not edited from this repository):** an explicit project root
per scope with no upward walk; raise with the offending path instead of swallowing a load error; no `sys.path` changes;
no working-directory fallback when a scope is named.

## 3. Risks found in repo-utils and the hub answer

Sources: the repo-utils sections and GAP entries of the evolvable-structure skill, plus the code they cite.

| # | Risk or oddity | Hub answer |
|---|---|---|
| R1 | Filesystem walk at import: wrappers attached per folder, so import cost and behaviour depend on what is on disk | Registry comes from declarations and record rows. Importing the package reads no directory. Records are read on first resolve, once. Test: inert import (section 4) |
| R2 | Git-root dependence: lookups depend on where the repository is | The hub's own code never asks where the repo is. But `esoi` still reads cwd, `ESOI_ROOT`/`ESOI_SNAPSHOT` and walks up for `esoi.toml`, so the hub closes this itself: a packaged snapshot read from package data, `environ` passed explicitly, and tests that resolve from a directory holding a hostile `esoi.toml` and from a `pip --target` vendored copy, asserting unchanged results, `sys.path` unchanged and snapshot equal to records. The `esoi` side is the section 2 proposal |
| R3 | First match by folder name wins silently | Keys are scope + solution id + name. `esoi.runtime.add` raises on a second declaration with a different object, but `register(..., replace=True)` can replace, so the hub wrapper refuses `replace` of any hub-declared name; consumers use their own names. Test: replacing a hub name raises |
| R4 | `sys.modules` wrapper magic changes identity, `isinstance` and tracebacks | No `sys.modules` edits. Resolve returns the real object |
| R5 | Env-var reload switch with truthiness trap (`"0"` turns it on) | The hub reads no environment itself: settings are config fields. `esoi.runtime` does read `ESOI_SELECT_*`, `ESOI_ROOT` and `ESOI_SNAPSHOT`, so passing `environ` from a config field (default `{}`) is the control, and a test proves an environment variable does not change a result. A scan for `os.environ` in the hub is secondary |
| R6 | Install-time bootstrap in `setup.py` writes files and installs packages | `pyproject.toml` only, declarative. Test: the build runs no hub code |
| R7 | Textual rename replaces substrings | Renames are record edits plus a checked symbol rename. `esoi check` fails a dangling id. No alias after a rename (section 4) |
| R8 | Documented but not implemented behaviour | Each documented behaviour has a named test. Metric selection is build time (`esoi select`), and the docs say so |
| R9 | Registry forked by copying | One registry (`esoi.runtime`), consumed as a dependency, never copied |
| R10 | Name and metadata drift | One test: package name, import name, changelog heading and `esoi.toml` package agree |
| R11 | Dependency pruning by text scan misses dynamic names | Extras per arm, generated from a per-arm import check (section 1). A missing extra at run time raises an error naming the extra |
| R12 | Swallowed errors | The hub adds no retry or swallow wrappers, and its own errors name the solution, scope and layer. `esoi` currently swallows some load errors; the section 2 proposal asks it to raise with the path, and until then the hub's tests assert a broken record fails visibly |
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
| Safe loading | Section 2 rules | `tests/test_safe_loading.py`: config value `os:system`, snapshot module `os`, filepath `../x.py`, and a look-alike `hubofhubs` module earlier on `sys.path`, all rejected |
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

Each step ends with its tests and one local commit by explicit path; nothing is pushed.

1. **Baseline by implementation id**: `scripts/baseline.py` writes `docs/baseline.json` (executed-line share per
   implementation id, not per module path); `--check` fails on a drop. Done.
2. **Import-boundary allowlist test**: `tests/test_import_boundary.py`. Done.
3. **Rename to `hubofhubs`, no alias**, in one change with the consumer's imports of the hub (coordinate with the
   consumer's owner; a later task). `pyproject.toml` and the distribution name follow here.
4. **No environment reads**, plus the hostile-directory and vendored-copy tests (R2, R5).
5. **Resolve wrapper and `assemble`**: cascade, refusal of `replace` on hub names, reason line.
6. **Needs from typed constructor parameters**, the generated `uses_solution_ids` check, and the graph checks (no cycles,
   every need resolves, external-seat rule).
7. **Per-seat import check, then the port move.** Moving ports "as they are" is impossible: 65 of the consumer's 106
   adapter modules import its core. For each seat, compute its imports first; move the Protocol and neutral helpers only;
   everything else arrives through `assemble`. The consumer keeps re-exports at the old paths. The seats to move are
   measured in the consumer before the move (a later task).
8. **Docs**: quickstart, versioning, releasing, changelog.
