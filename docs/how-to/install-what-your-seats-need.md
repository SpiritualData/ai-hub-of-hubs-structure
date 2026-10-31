# Install what your seats need

Use this to install the Python packages, and see the keys and programs, for the seats you actually use and nothing else. The
arms declare their needs beside the code (`REQUIRES`, shared pieces in `hubofhubs/arm_needs.py`); the full table is
[requirements by arm](../reference/requirements-by-arm.md), generated from those declarations.

## Plan, then install

```bash
esoi install --package hubofhubs --solution know-the-world
```

This prints the closure (the selected arm, the arms that fill its needs, the modules each imports, each with the reason it is
in), the commands it would run and what only you can do: set a key, install a program. It changes nothing. Add `--yes` inside a
virtualenv to run it. To plan for another arm, add `--arm seat=name`; for every arm, `--all-arms`.

## Check the variables, write a template

```bash
esoi requirements --package hubofhubs --check
esoi requirements --package hubofhubs --env-template .env.example
```

`.env.example` at the repository root is this command's output for the default assembly: names, official links and dated
free-tier facts, no values. `esoi requirements --package hubofhubs --env-file .env` adds the variables you are missing to your
own `.env`, commented out, and never changes a line you wrote.

## Check that the selected arms install together

```bash
esoi requirements --package hubofhubs --coherence
```

Exit code 1 means the selected arms need package versions that cannot coexist; the output shows the resolution ladder's
proposed fix. `tests/test_requirements.py` runs the offline form on every change; add `--online` to let pip check in a
temporary virtualenv. The explanation is in the esoi page on environment needs.
