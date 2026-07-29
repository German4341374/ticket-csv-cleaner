# Architecture

## Components

| Module | Responsibility |
| --- | --- |
| `csv_io.py` | Byte decoding, encoding confidence, delimiter detection, CSV parsing, and header mapping |
| `config.py` | Strict Pydantic validation of YAML rules |
| `normalize.py` | Pure text, lookup, duplicate-key, and date transformations |
| `models.py` | Canonical enums, domain record, findings, summaries, and output types |
| `duplicates.py` | Same-requester title similarity without retaining full rows |
| `masking.py` | Email and phone masking |
| `processor.py` | Ordered business-rule pipeline and row classification |
| `reporting.py` | Atomic CSV writes plus aggregate JSON and HTML reports |
| `preview.py` | Bounded masked terminal preview |
| `cli.py` | Typer commands and exit-code policy |

## Processing order

1. Read source bytes without modifying the original.
2. Detect encoding and decode text.
3. Detect a supported delimiter.
4. Map source headers to the canonical schema.
5. Remove fully empty rows.
6. Normalize text, status, priority, and dates.
7. Apply required-field, email, chronology, and domain-model validation.
8. Reject repeated ticket IDs.
9. Flag probable same-requester title duplicates.
10. Mask personal data.
11. Classify each row into exactly one output collection.
12. Write outputs atomically when the command is not a dry run.

Validation and duplicate matching use unmasked normalized values. Only masked values enter output models.

## Classification invariant

For every non-empty input row:

```text
clean XOR warnings XOR rejected
```

- Any error places the row in `rejected.csv`.
- No error plus at least one warning places it in `warnings.csv`.
- No findings places it in `clean.csv`.

This invariant prevents warning rows from silently entering an import file.

## Failure boundaries

File-level failures, such as an unreadable file, invalid YAML, missing header, unsupported delimiter, duplicate mapped header, or extra CSV value, stop processing with exit code `2`.

Row-level quality failures are accumulated. Outputs are still generated, and the command exits `1` when any row was rejected.

## Privacy model

The application has no network client. Reports contain only a source filename, format metadata, counts, and issue categories. Review CSV files necessarily contain ticket fields, so masking is enabled before any row is written.
