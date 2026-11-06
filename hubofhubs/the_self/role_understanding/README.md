# Role Understanding

**Purpose:** Give every part a role in the whole that the part and the Assembler can both read.

Breadcrumb: [Top](../../../esoi/README.md) > [The parts working as one whole](../README.md) > Role Understanding

Part of [The parts working as one whole](../README.md)

## Role Understanding (`role-understanding`)

- Out of scope: Building the parts, and deciding which arm of a part is best.
- Delegates to: the-assembler
- Entry call: `hubofhubs.run("role-understanding", 'the-assembler')`
- Selected implementation: Role checked against the part's calls (`checked_role`)
- Metric: Roles stated as recorded and contradictions found
- Implemented by: [`hubofhubs/the_self/__init__.py`](../__init__.py), [`hubofhubs/the_self/assembler/__init__.py`](../assembler/__init__.py), [`hubofhubs/the_self/assembler/arm_needs.py`](../assembler/arm_needs.py), [`hubofhubs/the_self/assembler/cli.py`](../assembler/cli.py), [`hubofhubs/the_self/assembler/interface.py`](../assembler/interface.py), [`hubofhubs/the_self/assembler/oneline.py`](../assembler/oneline.py), [`hubofhubs/the_self/assembler/resolution.py`](../assembler/resolution.py), [`hubofhubs/the_self/assembler/tests/test_safe_loading.py`](../assembler/tests/test_safe_loading.py) and 22 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Role as the record states it | `role-understanding:recorded_role` | States a part's purpose, what it is not responsible for and who owns that, word for word from the part's own row, and says so when no record knows the part. | [`hubofhubs/the_self/role_understanding/roles.py`](roles.py) |  |
| Role checked against the part's calls | `role-understanding:checked_role` | States the recorded role and adds the contradictions it has with the part's records and code: an owner that names no solution, a part that names itself as owner, and a call its code makes to a solution it neither uses nor delegates to. | [`hubofhubs/the_self/role_understanding/roles.py`](roles.py) | selected |

## Metrics

- Roles stated as recorded and contradictions found (`metric-role-understanding`): leader `checked_role`, 13 of 13 cases

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The parts working as one whole](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
