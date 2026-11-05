# Release the hub

The hub is released as a git tag. Consumers install it from the tag, so a release is the tag, then the consumers' pins, in that
order. This page is the plain list; nothing here is done by a script.

## What must be true first

1. The working tree is clean and `main` holds the release (`pyproject.toml` `version`, a `CHANGELOG.md` entry with the same number).
2. These pass: `python3 scripts/status.py`, `esoi check`, `python3 -m esoi.coherence --gate`, `esoi docs check`, `esoi hygiene`,
   and the tests of the files you touched (by file, never the whole suite).
3. `from hubofhubs.api import ...` resolves every public name: `python3 -m pytest tests/test_public_api.py`.
4. Quest AI Runner and quest-backend import only from `hubofhubs.api` and `hubofhubs.run`, so they are ready for the new layout
   (no `hubofhubs.<internal path>` import left in either; grep for `from hubofhubs\.` and expect only `hubofhubs.api`).
5. Quest AI Runner's own test `test_the_hub_rows_for_qar_cite_real_paths` passes against the registry rows.
6. Nobody has pushed `main` of the hub before the consumers are ready: production installs the hub and Quest AI Runner by git
   reference, and an old consumer on a new hub (or the reverse) breaks the next image build.

## Steps

1. Tag the release commit on `main` (annotated, local first): `git tag -a vX.Y.Z -m "hubofhubs X.Y.Z"`.
2. Update the consumers' pins from `@develop` to `@vX.Y.Z`: the `hubofhubs[...]` line in Quest AI Runner's `pyproject.toml` and in
   quest-backend's `requirements.txt` (its Dockerfile fetches the `develop` ref for cache busting: point it at the tag ref too).
   Update the install line of the hub's `README.md` the same way.
3. Release in this order, each one a human decision made by the release owner, never by a background process:
   hub first (push `main` and the tag), then Quest AI Runner (merge forward, push), then quest-backend (push, which rebuilds the
   image). Never push the hub alone while a consumer still pins `develop`.
4. After the pushes, install into a throwaway virtual environment under `/tmp` from the tag and run
   `python3 -c "import hubofhubs.api as a; [getattr(a, n) for n in a.__all__]"`.

## The local tag

The annotated tag `v0.3.0` is created locally on the release commit and not pushed. Delete it with `git tag -d v0.3.0` if the release
commit changes, and make it again.
