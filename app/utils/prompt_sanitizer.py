"""Sanitize user input for safe inclusion in GPT prompts."""
import re
from typing import Optional


# Region tags that delimit untrusted content in the GPT prompts
# (<USER_INPUT> for the user's query, <SEARCH_RESULTS> for the third-party
# search-snippet digest). A literal tag inside untrusted text would CLOSE the
# region and promote everything after it to trusted prompt text (M18
# PO-prompts-04), so both sides of the boundary neutralize the literals.
# Case-insensitive and whitespace-tolerant: "</ user_input >" is as dangerous
# as "</USER_INPUT>" to a model doing fuzzy tag matching.
_PROMPT_REGION_TAG_RE = re.compile(r'(?i)<\s*(/?)\s*(USER_INPUT|SEARCH_RESULTS)\s*>')


def neutralize_prompt_tags(text: str) -> str:
    """Neutralize literal prompt-region tag delimiters in untrusted text.

    Replaces the angle brackets with square brackets ("</USER_INPUT>" ->
    "[/USER_INPUT]") so the text can never open or close a prompt trust
    region, while keeping the content readable. Idempotent — the bracketed
    form no longer matches the tag pattern.
    """
    if not text:
        return ""
    return _PROMPT_REGION_TAG_RE.sub(lambda m: f'[{m.group(1)}{m.group(2)}]', text)


def sanitize_prompt_input(text: Optional[str], max_length: int = 200) -> str:
    """Sanitize user input for safe inclusion in GPT prompts.

    - Truncates to max_length
    - Strips control characters (keeps newlines, tabs, spaces)
    - Collapses excessive newlines (3+ -> 2)
    - Escapes triple-quotes and backticks (prompt delimiters)
    - Neutralizes literal region tags (<USER_INPUT>/<SEARCH_RESULTS>) so the
      input cannot escape the untrusted region it is wrapped in
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
    # Neutralize region-tag literals AFTER truncation so a tag straddling the
    # cut cannot survive intact (a truncated half-tag is inert anyway).
    text = neutralize_prompt_tags(text)
    return text.strip()


def sanitize_untrusted_block(text: Optional[str], max_length: Optional[int] = None) -> str:
    """Sanitize THIRD-PARTY text (search titles/snippets) for inclusion inside
    a delimited untrusted prompt region (M18 PO-prompts-05).

    Lighter than :func:`sanitize_prompt_input` — snippet digests are
    multi-kilobyte and legitimately contain quotes/newlines, so this only:

    - optionally truncates (callers usually cap the assembled digest instead)
    - strips control characters (keeps newlines, tabs, spaces)
    - neutralizes region-tag literals so a hostile page title/snippet cannot
      close the <SEARCH_RESULTS> (or <USER_INPUT>) region it is placed in
    """
    if not text:
        return ""
    if max_length is not None:
        text = text[:max_length]
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return neutralize_prompt_tags(text)


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
    # Literal prompt-region tags (M18 PO-prompts-04): angle-bracket tag syntax
    # only, so plain prose like "user input" or "search results" never flags.
    r'(?i)<\s*/?\s*(user_input|search_results)\s*>',
]


def check_injection_patterns(text: str) -> bool:
    """Return True if text contains suspicious prompt injection patterns.

    Uses multi-word sequences to minimize false positives on legitimate
    product queries. Single words like 'system' or 'instruction' are NOT flagged.
    """
    if not text:
        return False
    return any(re.search(p, text) for p in _INJECTION_PATTERNS)
