"""Safe CSV decoding, delimiter detection, and canonical column mapping."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from charset_normalizer import from_bytes

from ticket_csv_cleaner.config import CleanerConfig
from ticket_csv_cleaner.errors import InputError
from ticket_csv_cleaner.models import CANONICAL_COLUMNS, SourceMetadata
from ticket_csv_cleaner.normalize import normalize_text

SUPPORTED_DELIMITERS = ",;\t|"


@dataclass(frozen=True, slots=True)
class LoadedCsv:
    """Decoded canonical CSV rows and source metadata."""

    metadata: SourceMetadata
    rows: tuple[tuple[int, dict[str, str]], ...]


def detect_encoding(raw: bytes) -> tuple[str, str, float]:
    """Return decoded text, detected encoding, and a 0-1 confidence estimate."""
    if not raw:
        raise InputError("Input CSV is empty.")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig", 1.0

    best = from_bytes(raw).best()
    if best is None or best.encoding is None:
        raise InputError("Unable to detect the CSV encoding.")
    try:
        text = raw.decode(best.encoding)
    except (LookupError, UnicodeDecodeError) as exc:
        raise InputError(f"Unable to decode CSV as {best.encoding}.") from exc
    confidence = max(0.0, min(1.0, 1.0 - (float(best.percent_chaos) / 100.0)))
    return text, best.encoding.lower().replace("_", "-"), round(confidence, 4)


def detect_delimiter(text: str) -> str:
    """Detect a supported delimiter from the header and representative rows."""
    sample_lines = [line for line in text.splitlines()[:25] if line.strip()]
    if not sample_lines:
        raise InputError("Input CSV contains no non-empty rows.")
    sample = "\n".join(sample_lines)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=SUPPORTED_DELIMITERS)
    except csv.Error as exc:
        try:
            dialect = csv.Sniffer().sniff(sample_lines[0], delimiters=SUPPORTED_DELIMITERS)
        except csv.Error:
            raise InputError("Unable to detect a supported CSV delimiter.") from exc
    return dialect.delimiter


def normalized_header(value: str) -> str:
    """Normalize common header spelling while preserving explicit mapping support."""
    compact = normalize_text(value).casefold().replace("-", "_").replace(" ", "_")
    while "__" in compact:
        compact = compact.replace("__", "_")
    return compact


def canonical_header(value: str, config: CleanerConfig) -> str:
    """Resolve an input header through case-insensitive YAML mapping."""
    mapping = {
        normalized_header(source): target for source, target in config.column_mapping.items()
    }
    normalized = normalized_header(value)
    return mapping.get(normalized, normalized)


def load_csv(path: Path, config: CleanerConfig) -> LoadedCsv:
    """Load a CSV into canonical dictionaries without mutating field values."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError(f"Unable to read input CSV {path}: {exc}") from exc

    text, encoding, confidence = detect_encoding(raw)
    delimiter = detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    if reader.fieldnames is None:
        raise InputError("CSV header is missing.")

    mapped_headers = [canonical_header(header, config) for header in reader.fieldnames]
    duplicate_headers = sorted(
        {header for header in mapped_headers if mapped_headers.count(header) > 1}
    )
    if duplicate_headers:
        raise InputError(f"Multiple source columns map to: {', '.join(duplicate_headers)}.")

    missing = sorted(set(CANONICAL_COLUMNS) - set(mapped_headers))
    if missing:
        raise InputError(f"Missing expected columns: {', '.join(missing)}.")

    header_map = dict(zip(reader.fieldnames, mapped_headers, strict=True))
    rows: list[tuple[int, dict[str, str]]] = []
    for line_number, source_row in enumerate(reader, start=2):
        if None in source_row:
            raise InputError(f"Line {line_number} contains more values than the header.")
        canonical = dict.fromkeys(CANONICAL_COLUMNS, "")
        for source_name, value in source_row.items():
            mapped_name = header_map[source_name]
            if mapped_name in canonical:
                canonical[mapped_name] = value or ""
        rows.append((line_number, canonical))

    metadata = SourceMetadata(
        filename=path.name,
        encoding=encoding,
        encoding_confidence=confidence,
        delimiter=delimiter,
        columns=tuple(mapped_headers),
    )
    return LoadedCsv(metadata=metadata, rows=tuple(rows))
