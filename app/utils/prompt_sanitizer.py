"""Sanitize user input for safe inclusion in GPT prompts."""
import re
from typing import Optional


def sanitize_prompt_input(text: Optional[str], max_length: int = 200) -> str:
    """Sanitize user input for safe inclusion in GPT prompts.

    - Truncates to max_length
    - Strips control characters (keeps newlines, tabs, spaces)
    - Collapses excessive newlines (3+ -> 2)
    - Escapes triple-quotes and backticks (prompt delimiters)
    """
    if not text:
        return ""
    text = text[:max_length]
    # Strip control characters but keep \n \r \t and space
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Escape prompt delimiters
    text = text.replace('```', '` ` `')
    text = text.replace('"""', '" " "')
    return text.strip()


# Patterns that indicate prompt injection attempts.
# These require specific SEQUENCES (not single words) to avoid false positives
# on legitimate queries like "System of a Down" or "instruction manual".
_INJECTION_PATTERNS = [
    r'(?i)ignore\s+(all\s+)?previous\s+instructions',
    r'(?i)system\s*:\s*',
    r'(?i)you\s+are\s+now\s+',
    r'(?i)override\s+instructions',
    r'(?i)forget\s+(all\s+)?(your\s+)?instructions',
    r'(?i)new\s+instructions?\s*:',
    r'(?i)disregard\s+(all\s+)?(previous\s+)?instructions',
]


def check_injection_patterns(text: str) -> bool:
    """Return True if text contains suspicious prompt injection patterns.

    Uses multi-word sequences to minimize false positives on legitimate
    product queries. Single words like 'system' or 'instruction' are NOT flagged.
    """
    if not text:
        return False
    return any(re.search(p, text) for p in _INJECTION_PATTERNS)
