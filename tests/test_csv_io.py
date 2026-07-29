"""CSV format and header detection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ticket_csv_cleaner.config import CleanerConfig, default_config
from ticket_csv_cleaner.csv_io import (
    canonical_header,
    detect_delimiter,
    detect_encoding,
    load_csv,
    normalized_header,
)
from ticket_csv_cleaner.errors import InputError


def test_detects_utf8_encoding(correct_csv: Path) -> None:
    text, encoding, confidence = detect_encoding(correct_csv.read_bytes())
    assert "INC-001" in text
    assert encoding in {"ascii", "utf-8"}
    assert confidence > 0.9


def test_detects_utf8_bom() -> None:
    text, encoding, confidence = detect_encoding(b"\xef\xbb\xbfkey,value\none,two\n")
    assert text.startswith("key")
    assert encoding == "utf-8-sig"
    assert confidence == 1.0


def test_detects_cp1251_fixture(cp1251_csv: Path) -> None:
    loaded = load_csv(cp1251_csv, default_config())
    assert "1251" in loaded.metadata.encoding
    assert loaded.rows[0][1]["title"] == "Ошибка подключения"


def test_detects_utf16_fixture(utf16_csv: Path) -> None:
    loaded = load_csv(utf16_csv, default_config())
    assert "utf-16" in loaded.metadata.encoding
    assert loaded.rows[0][1]["ticket_id"] == "INC-051"


def test_detects_comma_delimiter(correct_csv: Path) -> None:
    loaded = load_csv(correct_csv, default_config())
    assert loaded.metadata.delimiter == ","


def test_detects_semicolon_delimiter(fixture_dir: Path) -> None:
    loaded = load_csv(fixture_dir / "semicolon.csv", default_config())
    assert loaded.metadata.delimiter == ";"
    assert loaded.rows[0][1]["ticket_id"] == "INC-030"


def test_detect_delimiter_rejects_single_column() -> None:
    with pytest.raises(InputError, match="delimiter"):
        detect_delimiter("only_header\nonly_value\n")


def test_empty_bytes_are_rejected() -> None:
    with pytest.raises(InputError, match="empty"):
        detect_encoding(b"")


def test_missing_expected_columns_are_reported(fixture_dir: Path) -> None:
    with pytest.raises(InputError, match="Missing expected columns"):
        load_csv(fixture_dir / "missing_columns.csv", default_config())


def test_column_mapping_is_case_insensitive(tmp_path: Path) -> None:
    path = tmp_path / "mapped.csv"
    path.write_text(
        "Ticket Number,Subject,Details,State,Severity,Requester,Owner,Created,Resolved\n"
        "INC-060,Mapped row,Details,open,low,user@example.test,Analyst,2026-01-01,\n",
        encoding="utf-8",
    )
    config = CleanerConfig(
        column_mapping={
            "ticket number": "ticket_id",
            "subject": "title",
            "details": "description",
            "state": "status",
            "severity": "priority",
            "requester": "requester_email",
            "owner": "assignee",
            "created": "created_at",
            "resolved": "resolved_at",
        }
    )
    loaded = load_csv(path, config)
    assert loaded.rows[0][1]["ticket_id"] == "INC-060"
    assert canonical_header("TICKET NUMBER", config) == "ticket_id"


def test_duplicate_mapped_headers_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicates.csv"
    path.write_text(
        "ticket_id,ID,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        "1,2,Title,Description,open,low,user@example.test,Owner,2026-01-01,\n",
        encoding="utf-8",
    )
    config = CleanerConfig(column_mapping={"ID": "ticket_id"})
    with pytest.raises(InputError, match="Multiple source columns map"):
        load_csv(path, config)


def test_extra_row_values_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "extra.csv"
    path.write_text(
        "ticket_id,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        "1,Title,Description,open,low,user@example.test,Owner,2026-01-01,,extra\n",
        encoding="utf-8",
    )
    with pytest.raises(InputError, match="more values"):
        load_csv(path, default_config())


def test_header_normalization_handles_spaces_and_hyphens() -> None:
    assert normalized_header(" Ticket--ID ") == "ticket_id"
