"""Pure normalization functions."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from dateutil import parser as date_parser

MULTISPACE = re.compile(r"[ \t]+")


def normalize_text(value: str | None) -> str:
    """Trim surrounding whitespace and normalize line endings and line whitespace."""
    if value is None:
        return ""
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [MULTISPACE.sub(" ", line).strip() for line in normalized.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def normalized_lookup(value: str, mapping: dict[str, str]) -> str | None:
    """Map a case-insensitive value after collapsing whitespace."""
    lookup = MULTISPACE.sub(" ", value).strip().casefold()
    normalized_mapping = {
        MULTISPACE.sub(" ", key).strip().casefold(): mapped for key, mapped in mapping.items()
    }
    return normalized_mapping.get(lookup)


def parse_datetime(value: str, formats: tuple[str, ...], *, day_first: bool) -> datetime:
    """Parse configured formats first and then use dateutil for common variants."""
    stripped = value.strip()
    for date_format in formats:
        try:
            return datetime.strptime(stripped, date_format)
        except ValueError:
            continue
    return date_parser.parse(stripped, dayfirst=day_first, fuzzy=False)


def format_datetime(value: datetime) -> str:
    """Serialize datetimes consistently, normalizing aware values to UTC."""
    if value.tzinfo is not None:
        utc_value = value.astimezone(UTC)
        return utc_value.isoformat(timespec="seconds").replace("+00:00", "Z")
    return value.isoformat(timespec="seconds")


def duplicate_text_key(value: str) -> str:
    """Create a stable comparison key for duplicate-title matching."""
    characters = (character if character.isalnum() else " " for character in value.casefold())
    return MULTISPACE.sub(" ", "".join(characters)).strip()
