"""Compact terminal preview rendering."""

from __future__ import annotations

from pathlib import Path

from ticket_csv_cleaner.config import CleanerConfig
from ticket_csv_cleaner.csv_io import LoadedCsv, load_csv
from ticket_csv_cleaner.masking import mask_email, mask_text
from ticket_csv_cleaner.normalize import normalize_text

PREVIEW_COLUMNS: tuple[str, ...] = (
    "ticket_id",
    "title",
    "status",
    "priority",
    "requester_email",
    "created_at",
)


def preview_source(path: Path, config: CleanerConfig, row_count: int) -> tuple[LoadedCsv, str]:
    """Return detected metadata and a masked pipe-delimited preview."""
    loaded = load_csv(path, config)
    display_rows: list[list[str]] = []
    for _, source in loaded.rows:
        normalized = {key: normalize_text(value) for key, value in source.items()}
        if all(not value for value in normalized.values()):
            continue
        if config.mask_personal_data:
            normalized["requester_email"] = mask_email(normalized["requester_email"])
            normalized["title"] = mask_text(normalized["title"])
        display_rows.append([truncate(normalized[column]) for column in PREVIEW_COLUMNS])
        if len(display_rows) >= row_count:
            break

    widths = [
        min(
            32,
            max(
                len(column),
                *(len(row[index]) for row in display_rows),
            ),
        )
        for index, column in enumerate(PREVIEW_COLUMNS)
    ]
    header = format_row(list(PREVIEW_COLUMNS), widths)
    separator = "-+-".join("-" * width for width in widths)
    body = [format_row(row, widths) for row in display_rows]
    return loaded, "\n".join([header, separator, *body])


def truncate(value: str, limit: int = 32) -> str:
    """Keep previews compact and single-line."""
    flattened = value.replace("\n", " ↵ ")
    return flattened if len(flattened) <= limit else f"{flattened[: limit - 1]}…"


def format_row(values: list[str], widths: list[int]) -> str:
    """Render one left-aligned preview row."""
    return " | ".join(
        value[:width].ljust(width) for value, width in zip(values, widths, strict=True)
    )
