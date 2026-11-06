# hands

Breadcrumb: [Top](../../../esoi/README.md) > [The form and internal context of a system](../README.md) > hands

Part of [The form and internal context of a system](../README.md)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Declaration only | `the-hands:declaration_only` | Lists the declared integrations as the declaration gives them and checks neither reach nor use: a list a registry can print, which cannot say that a declared integration is idle or cut off. | [`hubofhubs/the_body/hands/integrations.py`](integrations.py) |  |
| Declared and used | `the-hands:declared_and_used` | Lists each declared integration of the system with ``reachable`` (it names a ``tool`` the AI can call and is not marked ``disabled``) and ``used`` (a recent run record lists it in ``used``), and marks the ones declared but never used so they are reported rather than forgotten. | [`hubofhubs/the_body/hands/integrations.py`](integrations.py) | selected |

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The form and internal context of a system](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
