"""Exact and probable duplicate helpers."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from ticket_csv_cleaner.normalize import duplicate_text_key


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    """Minimal non-sensitive duplicate-comparison state."""

    line_number: int
    title_key: str
    requester_key: str


def probable_duplicate(
    title: str,
    requester: str,
    candidates: list[DuplicateCandidate],
    threshold: float,
) -> tuple[DuplicateCandidate, float] | None:
    """Find the strongest same-requester title match above a threshold."""
    title_key = duplicate_text_key(title)
    requester_key = requester.strip().casefold()
    if not title_key or not requester_key:
        return None

    best: tuple[DuplicateCandidate, float] | None = None
    for candidate in candidates:
        if candidate.requester_key != requester_key:
            continue
        score = SequenceMatcher(None, title_key, candidate.title_key, autojunk=False).ratio()
        if score >= threshold and (best is None or score > best[1]):
            best = (candidate, score)
    return best
