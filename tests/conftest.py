"""Shared safe CSV fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

HEADER = (
    "ticket_id,title,description,status,priority,requester_email,assignee,created_at,resolved_at\n"
)


@pytest.fixture
def fixture_dir() -> Path:
    """Return the committed fixture directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def correct_csv(fixture_dir: Path) -> Path:
    """Return a valid UTF-8 comma-delimited fixture."""
    return fixture_dir / "correct.csv"


@pytest.fixture
def cp1251_csv(tmp_path: Path) -> Path:
    """Create a deterministic Windows-1251 fixture without personal data."""
    content = (
        HEADER
        + "INC-050,Ошибка подключения,"
        + "Повторяющееся описание для точного определения кодировки,"
        + "open,high,example@example.test,Инженер,2026-06-01 08:00:00,\n"
    )
    path = tmp_path / "cp1251.csv"
    path.write_bytes(content.encode("cp1251"))
    return path


@pytest.fixture
def utf16_csv(tmp_path: Path) -> Path:
    """Create a deterministic UTF-16 fixture."""
    content = (
        HEADER
        + "INC-051,UTF-16 ticket,Encoding fixture,open,low,"
        + "example@example.test,Analyst,2026-06-01,\n"
    )
    path = tmp_path / "utf16.csv"
    path.write_bytes(content.encode("utf-16"))
    return path


@pytest.fixture
def single_valid_csv(tmp_path: Path) -> Path:
    """Create one valid canonical ticket."""
    path = tmp_path / "single.csv"
    path.write_text(
        HEADER
        + "INC-100,Network issue,Router restarted,open,high,"
        + "requester@example.test,Analyst,2026-01-02 10:00:00,\n",
        encoding="utf-8",
    )
    return path
