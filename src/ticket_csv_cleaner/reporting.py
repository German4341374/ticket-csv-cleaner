"""CSV, JSON, and HTML report generation."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO, cast

from jinja2 import Environment, PackageLoader, select_autoescape

from ticket_csv_cleaner.models import (
    CANONICAL_COLUMNS,
    OutputPaths,
    ProcessedRow,
    ProcessingResult,
)

ISSUE_COLUMNS: tuple[str, ...] = ("_line_number", "_issues")


def atomic_text_write(path: Path, writer: Callable[[TextIO], object]) -> None:
    """Write a UTF-8 file atomically within its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            writer(cast("TextIO", temporary))
            temporary.flush()
            os.fsync(temporary.fileno())
        Path(temporary_name).replace(path)
    except Exception:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
        raise


def issue_text(row: ProcessedRow) -> str:
    """Return deterministic issue text for review CSV files."""
    return " | ".join(f"{issue.code}: {issue.message}" for issue in row.issues)


def write_csv(path: Path, rows: tuple[ProcessedRow, ...], *, include_issues: bool) -> None:
    """Write canonical rows with optional review metadata."""

    def writer(handle: TextIO) -> None:
        fieldnames = list(CANONICAL_COLUMNS)
        if include_issues:
            fieldnames.extend(ISSUE_COLUMNS)
        csv_writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        csv_writer.writeheader()
        for row in rows:
            output = row.data.copy()
            if include_issues:
                output["_line_number"] = str(row.line_number)
                output["_issues"] = issue_text(row)
            csv_writer.writerow(output)

    atomic_text_write(path, writer)


def report_payload(result: ProcessingResult) -> dict[str, object]:
    """Build a privacy-conscious report without ticket row content."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": result.source.model_dump(mode="json"),
        "summary": result.summary.model_dump(mode="json"),
    }


def write_json_report(path: Path, result: ProcessingResult) -> None:
    """Write a deterministic, machine-readable quality report."""
    payload = report_payload(result)
    atomic_text_write(
        path,
        lambda handle: handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n"),
    )


def render_html_report(result: ProcessingResult) -> str:
    """Render a standalone HTML quality report."""
    environment = Environment(
        loader=PackageLoader("ticket_csv_cleaner", "templates"),
        autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True),
    )
    template = environment.get_template("report.html.j2")
    return template.render(report=report_payload(result))


def write_html_report(path: Path, result: ProcessingResult) -> None:
    """Write the standalone HTML quality report."""
    rendered = render_html_report(result)
    atomic_text_write(path, lambda handle: handle.write(rendered))


def write_outputs(result: ProcessingResult, output_dir: Path) -> OutputPaths:
    """Write all three CSV classes and both report formats."""
    paths = OutputPaths(
        clean_csv=output_dir / "clean.csv",
        rejected_csv=output_dir / "rejected.csv",
        warnings_csv=output_dir / "warnings.csv",
        json_report=output_dir / "report.json",
        html_report=output_dir / "report.html",
    )
    write_csv(paths.clean_csv, result.clean, include_issues=False)
    write_csv(paths.rejected_csv, result.rejected, include_issues=True)
    write_csv(paths.warnings_csv, result.warnings, include_issues=True)
    write_json_report(paths.json_report, result)
    write_html_report(paths.html_report, result)
    return paths
