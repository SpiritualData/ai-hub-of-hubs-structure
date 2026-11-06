# esoi_application

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > esoi_application

Part of [Holding a request to a measure](../README.md)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Append to description | `esoi-application:append_to_description` | Adds the change as a sentence to the end of the record's description: the longer-prompt way, where each correction makes the text longer and no field is edited. | [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](apply.py) |  |
| Record field edit | `esoi-application:record_field_edit` | Sets the one field a change names on the one record it names, in the table its kind belongs to (specs, metrics, quality profiles). It refuses a change whose target or field does not exist, whose kind is unknown or whose new value is empty or carries an em dash, and says why; a refused change leaves every record as it was. | [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](apply.py) | selected |

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
