"""Personal-data masking without retaining captured values."""

from __future__ import annotations

import re

EMAIL_IN_TEXT = re.compile(r"(?<![\w.+-])([^@\s]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w.-])")
PHONE_IN_TEXT = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")


def mask_email(value: str) -> str:
    """Partially mask the local and domain components of an email address."""

    def replacement(match: re.Match[str]) -> str:
        local = match.group(1)
        domain = match.group(2)
        domain_parts = domain.rsplit(".", maxsplit=1)
        domain_name = domain_parts[0]
        suffix = domain_parts[1] if len(domain_parts) == 2 else ""
        masked_local = f"{local[0]}***" if local else "***"
        masked_domain = f"{domain_name[0]}***" if domain_name else "***"
        return (
            f"{masked_local}@{masked_domain}.{suffix}"
            if suffix
            else f"{masked_local}@{masked_domain}"
        )

    return EMAIL_IN_TEXT.sub(replacement, value)


def mask_phones(value: str) -> str:
    """Replace phone numbers while retaining only their final two digits."""

    def replacement(match: re.Match[str]) -> str:
        digits = "".join(character for character in match.group(0) if character.isdigit())
        return f"[PHONE-***{digits[-2:]}]"

    return PHONE_IN_TEXT.sub(replacement, value)


def mask_text(value: str) -> str:
    """Mask emails and phone numbers embedded in free text."""
    return mask_phones(mask_email(value))
