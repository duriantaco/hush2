"""Secret masking — replace secret values in output text."""

from __future__ import annotations

import hashlib
from typing import Callable


def create_masker(secrets: dict[str, str], style: str = "full") -> Callable[[str], str]:
    """Create a masking function that replaces secret values in text.

    Styles:
        full    — [REDACTED]
        partial — first 2 + last 2 chars: sk...3x
        hash    — SHA-256 prefix: [sha:a1b2c3d4]
    """
    if not secrets:
        return lambda text: text

    replacements: list[tuple[str, str]] = []
    for name, value in secrets.items():
        if len(value) < 2:
            replacement = "[REDACTED]"
        elif style == "partial":
            if len(value) <= 4:
                replacement = "[REDACTED]"
            else:
                replacement = f"{value[:2]}...{value[-2:]}"
        elif style == "hash":
            h = hashlib.sha256(value.encode()).hexdigest()[:8]
            replacement = f"[sha:{h}]"
        else:
            replacement = "[REDACTED]"
        replacements.append((value, replacement))

    # Sort by length descending so longer secrets are replaced first
    replacements.sort(key=lambda x: len(x[0]), reverse=True)

    def masker(text: str) -> str:
        for secret_val, replacement in replacements:
            text = text.replace(secret_val, replacement)
        return text

    return masker
