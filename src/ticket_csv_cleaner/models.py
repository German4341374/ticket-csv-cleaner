"""Typed models shared across the processing pipeline."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CANONICAL_COLUMNS: tuple[str, ...] = (
    "ticket_id",
    "title",
    "description",
    "status",
    "priority",
    "requester_email",
    "assignee",
    "created_at",
    "resolved_at",
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TicketStatus(StrEnum):
    """Canonical ticket statuses."""

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class TicketPriority(StrEnum):
    """Canonical ticket priorities."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketRecord(BaseModel):
    """A validated and normalized Service Desk ticket."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ticket_id: str
    title: str
    description: str = ""
    status: TicketStatus
    priority: TicketPriority
    requester_email: str
    assignee: str = ""
    created_at: datetime
    resolved_at: datetime | None = None

    @field_validator("requester_email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        """Apply a small, dependency-free email sanity check."""
        if value and EMAIL_PATTERN.fullmatch(value) is None:
            raise ValueError("must be a valid email address")
        return value

    @model_validator(mode="after")
    def resolved_after_creation(self) -> TicketRecord:
        """Reject chronologically impossible tickets."""
        if self.resolved_at is None:
            return self
        created = comparable_datetime(self.created_at)
        resolved = comparable_datetime(self.resolved_at)
        if resolved < created:
            raise ValueError("resolved_at must not be earlier than created_at")
        return self


def comparable_datetime(value: datetime) -> datetime:
    """Return an aware UTC datetime for safe comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Issue(BaseModel):
    """A row-level validation error or warning."""

    model_config = ConfigDict(frozen=True)

    severity: Literal["error", "warning"]
    code: str
    field: str | None = None
    message: str


class ProcessedRow(BaseModel):
    """A canonical row and its data-quality findings."""

    model_config = ConfigDict(frozen=True)

    line_number: int = Field(ge=2)
    data: dict[str, str]
    issues: tuple[Issue, ...] = ()


class SourceMetadata(BaseModel):
    """Detected properties of the source CSV."""

    model_config = ConfigDict(frozen=True)

    filename: str
    encoding: str
    encoding_confidence: float = Field(ge=0, le=1)
    delimiter: str = Field(min_length=1, max_length=1)
    columns: tuple[str, ...]


class QualitySummary(BaseModel):
    """Aggregate data-quality metrics."""

    model_config = ConfigDict(frozen=True)

    input_rows: int = Field(ge=0)
    empty_rows_removed: int = Field(ge=0)
    clean_rows: int = Field(ge=0)
    warning_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    exact_duplicates: int = Field(ge=0)
    probable_duplicates: int = Field(ge=0)
    quality_score: float = Field(ge=0, le=100)
    error_counts: dict[str, int]
    warning_counts: dict[str, int]


class ProcessingResult(BaseModel):
    """Complete in-memory result before optional output writes."""

    model_config = ConfigDict(frozen=True)

    source: SourceMetadata
    summary: QualitySummary
    clean: tuple[ProcessedRow, ...]
    rejected: tuple[ProcessedRow, ...]
    warnings: tuple[ProcessedRow, ...]

    @property
    def has_errors(self) -> bool:
        """Return whether any input row was rejected."""
        return self.summary.rejected_rows > 0


class OutputPaths(BaseModel):
    """Files produced by a non-dry clean operation."""

    model_config = ConfigDict(frozen=True)

    clean_csv: Path
    rejected_csv: Path
    warnings_csv: Path
    json_report: Path
    html_report: Path
