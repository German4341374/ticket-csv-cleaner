"""Output CSV and report tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ticket_csv_cleaner.config import default_config
from ticket_csv_cleaner.processor import process_csv
from ticket_csv_cleaner.reporting import (
    issue_text,
    render_html_report,
    report_payload,
    write_outputs,
)


def test_write_outputs_creates_all_five_files(fixture_dir: Path, tmp_path: Path) -> None:
    result = process_csv(fixture_dir / "duplicates.csv", default_config())
    paths = write_outputs(result, tmp_path / "output")
    assert paths.clean_csv.exists()
    assert paths.rejected_csv.exists()
    assert paths.warnings_csv.exists()
    assert paths.json_report.exists()
    assert paths.html_report.exists()


def test_clean_csv_uses_canonical_header(correct_csv: Path, tmp_path: Path) -> None:
    result = process_csv(correct_csv, default_config())
    paths = write_outputs(result, tmp_path)
    with paths.clean_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert list(rows[0]) == [
        "ticket_id",
        "title",
        "description",
        "status",
        "priority",
        "requester_email",
        "assignee",
        "created_at",
        "resolved_at",
    ]


def test_review_csv_includes_line_and_issue(fixture_dir: Path, tmp_path: Path) -> None:
    result = process_csv(fixture_dir / "duplicates.csv", default_config())
    paths = write_outputs(result, tmp_path)
    with paths.rejected_csv.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["_line_number"] == "3"
    assert "duplicate_ticket_id" in row["_issues"]
    assert "duplicates line 2" in issue_text(result.rejected[0])


def test_json_report_excludes_ticket_content(correct_csv: Path, tmp_path: Path) -> None:
    result = process_csv(correct_csv, default_config())
    paths = write_outputs(result, tmp_path)
    payload = json.loads(paths.json_report.read_text(encoding="utf-8"))
    assert payload["summary"]["clean_rows"] == 2
    assert "Login issue" not in paths.json_report.read_text(encoding="utf-8")
    assert set(payload) == {"generated_at", "source", "summary"}


def test_html_report_is_standalone_and_excludes_rows(correct_csv: Path) -> None:
    result = process_csv(correct_csv, default_config())
    html = render_html_report(result)
    assert "<!doctype html>" in html
    assert "Ticket CSV quality report" in html
    assert "100.00" in html
    assert "Login issue" not in html


def test_report_payload_contains_detected_format(correct_csv: Path) -> None:
    result = process_csv(correct_csv, default_config())
    payload = report_payload(result)
    source = payload["source"]
    assert isinstance(source, dict)
    assert source["delimiter"] == ","
