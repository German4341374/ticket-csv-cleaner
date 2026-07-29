"""Typer command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from ticket_csv_cleaner import __version__
from ticket_csv_cleaner.config import load_config
from ticket_csv_cleaner.errors import CleanerError
from ticket_csv_cleaner.models import OutputPaths, ProcessingResult
from ticket_csv_cleaner.preview import preview_source
from ticket_csv_cleaner.processor import process_csv
from ticket_csv_cleaner.reporting import write_outputs

app = typer.Typer(
    name="ticket-csv-cleaner",
    help="Validate and clean Service Desk CSV exports before migration.",
    no_args_is_help=True,
    add_completion=False,
)

InputPath = Annotated[
    Path,
    typer.Argument(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Service Desk CSV export.",
    ),
]
ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="YAML transformation rules.",
    ),
]


def version_callback(value: bool) -> None:
    """Print the installed version and stop."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Validate and clean Service Desk CSV exports before migration."""


def fail(message: str, code: int = 2) -> NoReturn:
    """Print a concise operational error and exit."""
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code)


def run_processing(input_file: Path, config_path: Path | None) -> ProcessingResult:
    """Load configuration and process a source file with CLI-safe errors."""
    try:
        return process_csv(input_file, load_config(config_path))
    except CleanerError as exc:
        fail(str(exc))


def summary_text(result: ProcessingResult) -> str:
    """Render a compact quality summary."""
    summary = result.summary
    delimiter = "\\t" if result.source.delimiter == "\t" else result.source.delimiter
    lines = [
        f"Source: {result.source.filename}",
        (
            f"Detected: encoding={result.source.encoding} "
            f"(confidence={result.source.encoding_confidence:.0%}), delimiter={delimiter!r}"
        ),
        f"Input rows: {summary.input_rows}",
        f"Empty rows removed: {summary.empty_rows_removed}",
        f"Clean rows: {summary.clean_rows}",
        f"Warning rows: {summary.warning_rows}",
        f"Rejected rows: {summary.rejected_rows}",
        f"Exact duplicates: {summary.exact_duplicates}",
        f"Probable duplicates: {summary.probable_duplicates}",
        f"Quality score: {summary.quality_score:.2f}/100",
    ]
    if summary.error_counts:
        lines.append(
            "Errors: " + ", ".join(f"{key}={value}" for key, value in summary.error_counts.items())
        )
    if summary.warning_counts:
        lines.append(
            "Warnings: "
            + ", ".join(f"{key}={value}" for key, value in summary.warning_counts.items())
        )
    return "\n".join(lines)


def output_text(paths: OutputPaths) -> str:
    """Render output paths after a successful write."""
    return "\n".join(
        [
            f"Clean CSV: {paths.clean_csv}",
            f"Rejected CSV: {paths.rejected_csv}",
            f"Warnings CSV: {paths.warnings_csv}",
            f"JSON report: {paths.json_report}",
            f"HTML report: {paths.html_report}",
        ]
    )


@app.command()
def validate(
    input_file: InputPath,
    config: ConfigOption = None,
) -> None:
    """Validate a CSV and print its data-quality summary without writing files."""
    result = run_processing(input_file, config)
    typer.echo(summary_text(result))
    if result.has_errors:
        raise typer.Exit(1)


@app.command()
def clean(
    input_file: InputPath,
    config: ConfigOption = None,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            file_okay=False,
            resolve_path=True,
            help="Destination for CSV files and reports.",
        ),
    ] = Path("output"),
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Process everything without writing output files."),
    ] = False,
) -> None:
    """Clean a CSV, split row classes, and generate quality reports."""
    result = run_processing(input_file, config)
    typer.echo(summary_text(result))
    if dry_run:
        typer.echo("Dry run: no files were written.")
    else:
        try:
            paths = write_outputs(result, output_dir)
        except OSError as exc:
            fail(f"Unable to write output files: {exc}")
        typer.echo(output_text(paths))
    if result.has_errors:
        raise typer.Exit(1)


@app.command()
def preview(
    input_file: InputPath,
    config: ConfigOption = None,
    rows: Annotated[
        int,
        typer.Option("--rows", "-n", min=1, max=100, help="Number of non-empty rows to show."),
    ] = 10,
) -> None:
    """Show masked, normalized source rows without writing files."""
    try:
        loaded, table = preview_source(input_file, load_config(config), rows)
    except CleanerError as exc:
        fail(str(exc))
    delimiter = "\\t" if loaded.metadata.delimiter == "\t" else loaded.metadata.delimiter
    typer.echo(f"Detected encoding={loaded.metadata.encoding}, delimiter={delimiter!r}\n{table}")


if __name__ == "__main__":
    app()
