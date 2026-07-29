"""Typer command integration tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ticket_csv_cleaner.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "1.0.0"


def test_validate_clean_file_exits_zero(correct_csv: Path) -> None:
    result = runner.invoke(app, ["validate", str(correct_csv)])
    assert result.exit_code == 0
    assert "Clean rows: 2" in result.stdout
    assert "Quality score: 100.00/100" in result.stdout


def test_validate_rejected_rows_exits_one(fixture_dir: Path) -> None:
    result = runner.invoke(app, ["validate", str(fixture_dir / "malformed_dates.csv")])
    assert result.exit_code == 1
    assert "Rejected rows: 2" in result.stdout
    assert "invalid_date" in result.stdout


def test_clean_writes_outputs(correct_csv: Path, tmp_path: Path) -> None:
    output = tmp_path / "result"
    result = runner.invoke(
        app,
        ["clean", str(correct_csv), "--output-dir", str(output)],
    )
    assert result.exit_code == 0
    assert (output / "clean.csv").exists()
    assert (output / "report.html").exists()
    assert "HTML report:" in result.stdout


def test_clean_with_rejections_writes_files_and_exits_one(
    fixture_dir: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "review"
    result = runner.invoke(
        app,
        [
            "clean",
            str(fixture_dir / "duplicates.csv"),
            "--output-dir",
            str(output),
        ],
    )
    assert result.exit_code == 1
    assert (output / "rejected.csv").exists()
    assert (output / "warnings.csv").exists()


def test_dry_run_writes_nothing(correct_csv: Path, tmp_path: Path) -> None:
    output = tmp_path / "dry"
    result = runner.invoke(
        app,
        ["clean", str(correct_csv), "--output-dir", str(output), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "Dry run: no files were written." in result.stdout
    assert not output.exists()


def test_preview_limits_rows_and_masks_email(correct_csv: Path) -> None:
    result = runner.invoke(app, ["preview", str(correct_csv), "--rows", "1"])
    assert result.exit_code == 0
    assert "INC-001" in result.stdout
    assert "INC-002" not in result.stdout
    assert "p***@e***.test" in result.stdout


def test_missing_columns_are_an_operational_error(fixture_dir: Path) -> None:
    result = runner.invoke(app, ["validate", str(fixture_dir / "missing_columns.csv")])
    assert result.exit_code == 2
    assert "Missing expected columns" in result.output
