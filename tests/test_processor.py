"""End-to-end processing rule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ticket_csv_cleaner.config import CleanerConfig, default_config
from ticket_csv_cleaner.processor import process_csv, quality_score


@pytest.mark.integration
def test_correct_csv_produces_only_clean_rows(correct_csv: Path) -> None:
    result = process_csv(correct_csv, default_config())
    assert result.summary.clean_rows == 2
    assert result.summary.rejected_rows == 0
    assert result.summary.warning_rows == 0
    assert result.summary.quality_score == 100
    assert result.has_errors is False


def test_text_status_priority_and_dates_are_normalized(correct_csv: Path) -> None:
    result = process_csv(correct_csv, default_config())
    first = result.clean[0].data
    second = result.clean[1].data
    assert first["description"] == "Needs investigation"
    assert first["status"] == "Open"
    assert first["priority"] == "High"
    assert first["created_at"] == "2026-01-10T09:00:00"
    assert second["resolved_at"] == "2026-01-10T10:30:00"


def test_output_masks_requester_email_by_default(correct_csv: Path) -> None:
    result = process_csv(correct_csv, default_config())
    assert result.clean[0].data["requester_email"] == "p***@e***.test"


def test_masking_can_be_disabled(correct_csv: Path) -> None:
    result = process_csv(correct_csv, CleanerConfig(mask_personal_data=False))
    assert result.clean[0].data["requester_email"] == "person1@example.test"


def test_fully_empty_rows_are_removed() -> None:
    source = Path(__file__).parent.parent / "examples" / "tickets.csv"
    result = process_csv(source, default_config())
    assert result.summary.empty_rows_removed == 1


def test_malformed_dates_and_date_order_are_rejected(fixture_dir: Path) -> None:
    result = process_csv(fixture_dir / "malformed_dates.csv", default_config())
    assert result.summary.rejected_rows == 2
    assert result.summary.error_counts["invalid_date"] == 1
    assert result.summary.error_counts["invalid_date_order"] == 1


def test_exact_and_probable_duplicates_are_split(fixture_dir: Path) -> None:
    result = process_csv(fixture_dir / "duplicates.csv", default_config())
    assert result.summary.clean_rows == 1
    assert result.summary.rejected_rows == 1
    assert result.summary.warning_rows == 1
    assert result.summary.exact_duplicates == 1
    assert result.summary.probable_duplicates == 1
    assert result.rejected[0].issues[0].code == "duplicate_ticket_id"
    assert result.warnings[0].issues[0].code == "probable_duplicate"


def test_probable_duplicates_require_same_requester(tmp_path: Path) -> None:
    path = tmp_path / "different-requesters.csv"
    path.write_text(
        "ticket_id,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        "1,VPN timeout,First,open,low,first@example.test,A,2026-01-01,\n"
        "2,VPN timeout!,Second,open,low,second@example.test,A,2026-01-01,\n",
        encoding="utf-8",
    )
    result = process_csv(path, default_config())
    assert result.summary.clean_rows == 2
    assert result.summary.warning_rows == 0


def test_missing_required_values_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing-value.csv"
    path.write_text(
        "ticket_id,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        "1,,Details,open,low,user@example.test,A,2026-01-01,\n",
        encoding="utf-8",
    )
    result = process_csv(path, default_config())
    assert result.summary.error_counts == {"missing_required": 1}
    assert result.rejected[0].issues[0].field == "title"


def test_unknown_status_and_priority_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unknown-values.csv"
    path.write_text(
        "ticket_id,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        "1,Title,Details,waiting,blocker,user@example.test,A,2026-01-01,\n",
        encoding="utf-8",
    )
    result = process_csv(path, default_config())
    assert result.summary.error_counts == {"unknown_priority": 1, "unknown_status": 1}


def test_invalid_email_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad-email.csv"
    path.write_text(
        "ticket_id,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        "1,Title,Details,open,low,invalid-email,A,2026-01-01,\n",
        encoding="utf-8",
    )
    result = process_csv(path, default_config())
    assert result.summary.error_counts["invalid_email"] == 1


def test_embedded_email_and_phone_are_masked(tmp_path: Path) -> None:
    path = tmp_path / "personal-data.csv"
    path.write_text(
        "ticket_id,title,description,status,priority,requester_email,"
        "assignee,created_at,resolved_at\n"
        '1,Contact user@example.test,"Call +1 202 555 0147",open,low,'
        "user@example.test,A,2026-01-01,\n",
        encoding="utf-8",
    )
    data = process_csv(path, default_config()).clean[0].data
    assert data["title"] == "Contact u***@e***.test"
    assert data["description"] == "Call [PHONE-***47]"


@pytest.mark.parametrize(
    ("clean", "warnings", "rejected", "expected"),
    [
        (0, 0, 0, 100.0),
        (4, 0, 0, 100.0),
        (3, 1, 0, 93.75),
        (3, 0, 1, 75.0),
        (0, 0, 1, 0.0),
    ],
)
def test_quality_score(
    clean: int,
    warnings: int,
    rejected: int,
    expected: float,
) -> None:
    assert quality_score(clean, warnings, rejected) == expected
