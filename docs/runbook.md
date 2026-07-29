# Operations runbook

## Preserve the source

Never clean the only copy of an export. The application reads the source without modifying it, but operators should keep the original file and record its checksum before a migration.

```bash
sha256sum tickets.csv
ticket-csv-cleaner validate tickets.csv --config rules.yaml
```

## Unexpected file-level failure

1. Run `preview` to display encoding and delimiter detection.
2. Confirm the export is a real CSV rather than an XLSX file with a renamed extension.
3. Inspect only the header using a safe local editor.
4. Add vendor headers to `column_mapping`.
5. Re-export files with inconsistent column counts instead of manually deleting values.

File-level failures return exit code `2` and write nothing.

## Unexpected rejected rows

1. Open `report.html` to identify the dominant error category.
2. Filter `rejected.csv` by `_issues`.
3. Correct the source system or a copied staging export.
4. Run `validate` again.
5. Import only `clean.csv` after the business owner approves warnings.

Do not remove an error rule solely to make a quality score green.

## Excess probable duplicates

1. Review whether titles are genuinely repetitive for the same requester.
2. Increase `probable_duplicate_threshold` in small increments.
3. Keep the threshold between `0.5` and `1.0`.
4. Re-run in dry-run mode before producing new files.

## Ambiguous dates

1. Obtain the source system's documented export format.
2. Add its exact `strptime` pattern at the beginning of `date_formats`.
3. Set `day_first`.
4. Add a regression fixture before using the rule in migration.

## Sensitive output

If unmasked personal data was produced:

1. Stop sharing or copying the output.
2. Restrict access to the output directory.
3. Delete it according to the organization's retention procedure.
4. Re-run with `mask_personal_data: true`.
5. Review custom sensitive formats that the built-in patterns did not detect.
