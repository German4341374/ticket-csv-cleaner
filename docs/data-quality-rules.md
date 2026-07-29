# Data-quality rules

## Errors

| Code | Condition | Result |
| --- | --- | --- |
| `missing_required` | A configured required value is blank | Rejected |
| `unknown_status` | Status is not present in `status_mapping` | Rejected |
| `unknown_priority` | Priority is not present in `priority_mapping` | Rejected |
| `invalid_date` | A non-empty date cannot be parsed | Rejected |
| `invalid_date_order` | Resolution is earlier than creation | Rejected |
| `invalid_email` | A non-empty requester address fails a basic syntax check | Rejected |
| `duplicate_ticket_id` | A case-insensitive ticket ID appeared earlier | Rejected |
| `model_validation` | The final typed Pydantic boundary fails | Rejected |

## Warnings

| Code | Condition | Result |
| --- | --- | --- |
| `probable_duplicate` | Same requester and normalized title similarity meets the configured threshold | Manual review |

Probable matching uses Python's deterministic `SequenceMatcher` after lowercasing the title and replacing punctuation with spaces. It is deliberately conservative: records from different requester addresses are never compared.

## Dates

Configured `date_formats` are attempted in order. `python-dateutil` is used only after all exact formats fail. Aware values are normalized to UTC with a `Z` suffix. Naive values remain naive because the source timezone is unknown.

For ambiguous values such as `03/04/2026`, configure an exact format or set `day_first` deliberately.

## Personal-data masking

- `alex@example.test` becomes `a***@e***.test`.
- `+1 202 555 0147` becomes `[PHONE-***47]`.
- Masking applies to requester email, title, description, and assignee.

Masking occurs after validation and duplicate comparison. Disable it only when protected downstream processing explicitly requires original values.
