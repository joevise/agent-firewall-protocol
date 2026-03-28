from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=256)
def compile_pattern(pattern: str) -> re.Pattern:
    """Compile and cache a regex pattern (case-insensitive)."""
    return re.compile(pattern, re.IGNORECASE)


def matches(pattern: str, text: str) -> bool:
    """Check if text matches a regex pattern."""
    if not text:
        return False
    return bool(compile_pattern(pattern).search(text))
