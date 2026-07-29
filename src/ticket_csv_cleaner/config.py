"""YAML configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ticket_csv_cleaner.errors import ConfigurationError
from ticket_csv_cleaner.models import CANONICAL_COLUMNS

DEFAULT_STATUS_MAPPING: dict[str, str] = {
    "new": "Open",
    "open": "Open",
    "opened": "Open",
    "in progress": "In Progress",
    "in_progress": "In Progress",
    "pending": "In Progress",
    "resolved": "Resolved",
    "solved": "Resolved",
    "closed": "Closed",
}

DEFAULT_PRIORITY_MAPPING: dict[str, str] = {
    "low": "Low",
    "p4": "Low",
    "medium": "Medium",
    "normal": "Medium",
    "p3": "Medium",
    "high": "High",
    "p2": "High",
    "critical": "Critical",
    "urgent": "Critical",
    "p1": "Critical",
}


class CleanerConfig(BaseModel):
    """Validated transformation and quality rules."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    column_mapping: dict[str, str] = Field(default_factory=dict)
    status_mapping: dict[str, str] = Field(default_factory=lambda: DEFAULT_STATUS_MAPPING.copy())
    priority_mapping: dict[str, str] = Field(
        default_factory=lambda: DEFAULT_PRIORITY_MAPPING.copy()
    )
    required_fields: tuple[str, ...] = (
        "ticket_id",
        "title",
        "status",
        "priority",
        "requester_email",
        "created_at",
    )
    date_formats: tuple[str, ...] = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
        "%Y/%m/%d",
        "%Y-%m-%d",
    )
    day_first: bool = False
    mask_personal_data: bool = True
    probable_duplicate_threshold: float = Field(default=0.88, ge=0.5, le=1.0)

    @field_validator("column_mapping")
    @classmethod
    def valid_column_targets(cls, value: dict[str, str]) -> dict[str, str]:
        """Allow mappings only to known canonical fields."""
        invalid = sorted(set(value.values()) - set(CANONICAL_COLUMNS))
        if invalid:
            raise ValueError(f"unknown canonical columns: {', '.join(invalid)}")
        return value

    @field_validator("required_fields")
    @classmethod
    def valid_required_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Ensure row requirements name canonical fields."""
        invalid = sorted(set(value) - set(CANONICAL_COLUMNS))
        if invalid:
            raise ValueError(f"unknown required fields: {', '.join(invalid)}")
        return value


def default_config() -> CleanerConfig:
    """Return independent default rules."""
    return CleanerConfig()


def load_config(path: Path | None) -> CleanerConfig:
    """Load a YAML rules file or return defaults."""
    if path is None:
        return default_config()
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Unable to read configuration {path}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a YAML mapping.")
    try:
        return CleanerConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid configuration: {exc}") from exc
