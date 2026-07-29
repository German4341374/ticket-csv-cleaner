"""Normalization and masking unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from ticket_csv_cleaner.masking import mask_email, mask_phones, mask_text
from ticket_csv_cleaner.normalize import (
    duplicate_text_key,
    format_datetime,
    normalize_text,
    normalized_lookup,
    parse_datetime,
)


def test_normalize_text_trims_and_normalizes_line_endings() -> None:
    assert normalize_text(" \r\n  first   line \r second\tline \n ") == "first line\nsecond line"


def test_normalize_text_replaces_non_breaking_spaces() -> None:
    assert normalize_text("one\u00a0\u00a0two") == "one two"


def test_normalized_lookup_is_case_insensitive() -> None:
    assert normalized_lookup("  IN   PROGRESS ", {"in progress": "In Progress"}) == "In Progress"


def test_normalized_lookup_returns_none_for_unknown_value() -> None:
    assert normalized_lookup("waiting", {"open": "Open"}) is None


@pytest.mark.parametrize(
    ("value", "expected_year", "expected_hour"),
    [
        ("2026-01-02T03:04:05+00:00", 2026, 3),
        ("2026-01-02 03:04:05", 2026, 3),
        ("02.01.2026 03:04", 2026, 3),
        ("01/02/2026 03:04 AM", 2026, 3),
    ],
)
def test_parse_multiple_date_formats(value: str, expected_year: int, expected_hour: int) -> None:
    parsed = parse_datetime(
        value,
        (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%m/%d/%Y %I:%M %p",
        ),
        day_first=False,
    )
    assert parsed.year == expected_year
    assert parsed.hour == expected_hour


def test_dateutil_fallback_honors_day_first() -> None:
    parsed = parse_datetime("03/04/2026", (), day_first=True)
    assert (parsed.month, parsed.day) == (4, 3)


def test_format_datetime_preserves_naive_time() -> None:
    assert format_datetime(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05"


def test_format_datetime_normalizes_offset_to_utc() -> None:
    source_timezone = timezone(timedelta(hours=2))
    value = datetime(2026, 1, 2, 3, 0, tzinfo=source_timezone)
    assert format_datetime(value) == "2026-01-02T01:00:00Z"
    assert value.astimezone(UTC).hour == 1


def test_duplicate_key_ignores_case_and_punctuation() -> None:
    assert duplicate_text_key(" VPN timeout! ") == duplicate_text_key("vpn timeout")


def test_mask_email_masks_local_and_domain() -> None:
    assert mask_email("alex@example.test") == "a***@e***.test"


def test_mask_email_inside_text() -> None:
    assert mask_text("Contact alex@example.test now") == "Contact a***@e***.test now"


def test_mask_phone_keeps_only_last_two_digits() -> None:
    masked = mask_phones("Call +1 (202) 555-0147 for details")
    assert masked == "Call [PHONE-***47] for details"
    assert "202" not in masked


def test_mask_text_leaves_non_sensitive_text_unchanged() -> None:
    assert mask_text("No personal data in this message") == "No personal data in this message"
