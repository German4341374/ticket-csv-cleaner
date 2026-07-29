"""CSV cleaning and data-quality business rules."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from dateutil.parser import ParserError
from pydantic import ValidationError

from ticket_csv_cleaner.config import CleanerConfig
from ticket_csv_cleaner.csv_io import load_csv
from ticket_csv_cleaner.duplicates import DuplicateCandidate, probable_duplicate
from ticket_csv_cleaner.masking import mask_email, mask_text
from ticket_csv_cleaner.models import (
    CANONICAL_COLUMNS,
    EMAIL_PATTERN,
    Issue,
    ProcessedRow,
    ProcessingResult,
    QualitySummary,
    TicketRecord,
    comparable_datetime,
)
from ticket_csv_cleaner.normalize import (
    duplicate_text_key,
    format_datetime,
    normalize_text,
    normalized_lookup,
    parse_datetime,
)

FREE_TEXT_FIELDS = ("title", "description", "assignee")


def error(code: str, message: str, field: str | None = None) -> Issue:
    """Create a consistent error issue."""
    return Issue(severity="error", code=code, field=field, message=message)


def warning(code: str, message: str, field: str | None = None) -> Issue:
    """Create a consistent warning issue."""
    return Issue(severity="warning", code=code, field=field, message=message)


def is_empty_row(row: dict[str, str]) -> bool:
    """Return whether every canonical value is blank."""
    return all(not normalize_text(value) for value in row.values())


def parse_date_field(
    data: dict[str, str],
    field: str,
    config: CleanerConfig,
    issues: list[Issue],
) -> datetime | None:
    """Parse and normalize one optional date field."""
    value = data[field]
    if not value:
        return None
    try:
        parsed = parse_datetime(value, config.date_formats, day_first=config.day_first)
    except (ValueError, OverflowError, ParserError):
        issues.append(
            error(
                "invalid_date",
                f"{field} cannot be parsed as a supported date.",
                field,
            )
        )
        return None
    data[field] = format_datetime(parsed)
    return parsed


def apply_masking(data: dict[str, str], config: CleanerConfig) -> dict[str, str]:
    """Mask personal data after validation and duplicate matching."""
    masked = data.copy()
    if not config.mask_personal_data:
        return masked
    masked["requester_email"] = mask_email(masked["requester_email"])
    for field in FREE_TEXT_FIELDS:
        masked[field] = mask_text(masked[field])
    return masked


def pydantic_issues(
    data: dict[str, str],
    created_at: datetime | None,
    resolved_at: datetime | None,
) -> list[Issue]:
    """Use the domain model as a final typed validation boundary."""
    if created_at is None:
        return []
    payload: dict[str, object] = {
        **data,
        "created_at": created_at,
        "resolved_at": resolved_at,
    }
    try:
        TicketRecord.model_validate(payload)
    except ValidationError as exc:
        findings: list[Issue] = []
        for validation_error in exc.errors():
            location = ".".join(str(part) for part in validation_error["loc"])
            findings.append(
                error(
                    "model_validation",
                    str(validation_error["msg"]),
                    location or None,
                )
            )
        return findings
    return []


def quality_score(clean_count: int, warning_count: int, rejected_count: int) -> float:
    """Score clean rows fully, warning rows at 75%, and rejected rows at zero."""
    total = clean_count + warning_count + rejected_count
    if total == 0:
        return 100.0
    return round(((clean_count + warning_count * 0.75) / total) * 100, 2)


def process_csv(path: Path, config: CleanerConfig) -> ProcessingResult:
    """Validate, normalize, classify, and mask every non-empty CSV row."""
    loaded = load_csv(path, config)
    clean_rows: list[ProcessedRow] = []
    rejected_rows: list[ProcessedRow] = []
    warning_rows: list[ProcessedRow] = []
    seen_ticket_ids: dict[str, int] = {}
    candidates: list[DuplicateCandidate] = []
    empty_rows = 0

    for line_number, source_data in loaded.rows:
        if is_empty_row(source_data):
            empty_rows += 1
            continue

        data = {field: normalize_text(source_data[field]) for field in CANONICAL_COLUMNS}
        issues: list[Issue] = []

        issues.extend(
            error("missing_required", f"{field} is required.", field)
            for field in config.required_fields
            if not data[field]
        )

        mapped_status = normalized_lookup(data["status"], config.status_mapping)
        if data["status"] and mapped_status is None:
            issues.append(
                error("unknown_status", f"Unsupported status: {data['status']}.", "status")
            )
        elif mapped_status is not None:
            data["status"] = mapped_status

        mapped_priority = normalized_lookup(data["priority"], config.priority_mapping)
        if data["priority"] and mapped_priority is None:
            issues.append(
                error(
                    "unknown_priority",
                    f"Unsupported priority: {data['priority']}.",
                    "priority",
                )
            )
        elif mapped_priority is not None:
            data["priority"] = mapped_priority

        created_at = parse_date_field(data, "created_at", config, issues)
        resolved_at = parse_date_field(data, "resolved_at", config, issues)
        if (
            created_at is not None
            and resolved_at is not None
            and comparable_datetime(resolved_at) < comparable_datetime(created_at)
        ):
            issues.append(
                error(
                    "invalid_date_order",
                    "resolved_at must not be earlier than created_at.",
                    "resolved_at",
                )
            )

        requester_email = data["requester_email"]
        if requester_email and EMAIL_PATTERN.fullmatch(requester_email) is None:
            issues.append(
                error(
                    "invalid_email",
                    "requester_email must be a valid email address.",
                    "requester_email",
                )
            )

        ticket_id = data["ticket_id"].casefold()
        if ticket_id:
            first_line = seen_ticket_ids.get(ticket_id)
            if first_line is None:
                seen_ticket_ids[ticket_id] = line_number
            else:
                issues.append(
                    error(
                        "duplicate_ticket_id",
                        f"ticket_id duplicates line {first_line}.",
                        "ticket_id",
                    )
                )

        if not any(issue.severity == "error" for issue in issues):
            issues.extend(pydantic_issues(data, created_at, resolved_at))

        if not any(issue.severity == "error" for issue in issues):
            match = probable_duplicate(
                data["title"],
                data["requester_email"],
                candidates,
                config.probable_duplicate_threshold,
            )
            if match is not None:
                candidate, similarity = match
                issues.append(
                    warning(
                        "probable_duplicate",
                        (
                            f"Title and requester resemble line {candidate.line_number} "
                            f"({similarity:.0%} title similarity)."
                        ),
                        "title",
                    )
                )
            candidates.append(
                DuplicateCandidate(
                    line_number=line_number,
                    title_key=duplicate_text_key(data["title"]),
                    requester_key=data["requester_email"].casefold(),
                )
            )

        processed = ProcessedRow(
            line_number=line_number,
            data=apply_masking(data, config),
            issues=tuple(issues),
        )
        if any(issue.severity == "error" for issue in issues):
            rejected_rows.append(processed)
        elif issues:
            warning_rows.append(processed)
        else:
            clean_rows.append(processed)

    all_issues = [issue for row in [*rejected_rows, *warning_rows] for issue in row.issues]
    error_counts = Counter(issue.code for issue in all_issues if issue.severity == "error")
    warning_counts = Counter(issue.code for issue in all_issues if issue.severity == "warning")
    summary = QualitySummary(
        input_rows=len(loaded.rows),
        empty_rows_removed=empty_rows,
        clean_rows=len(clean_rows),
        warning_rows=len(warning_rows),
        rejected_rows=len(rejected_rows),
        exact_duplicates=error_counts["duplicate_ticket_id"],
        probable_duplicates=warning_counts["probable_duplicate"],
        quality_score=quality_score(
            len(clean_rows),
            len(warning_rows),
            len(rejected_rows),
        ),
        error_counts=dict(sorted(error_counts.items())),
        warning_counts=dict(sorted(warning_counts.items())),
    )
    return ProcessingResult(
        source=loaded.metadata,
        summary=summary,
        clean=tuple(clean_rows),
        rejected=tuple(rejected_rows),
        warnings=tuple(warning_rows),
    )
