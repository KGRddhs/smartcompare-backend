"""Hybrid DIY install-survival attribution.

Replaces Branch.io after its free tier paywalled to $199/mo. Parses raw
Play Install Referrer payloads (Android) and clipboard payloads (iOS) into
canonical QR-XXXXXX invite codes for handoff to referral_service.

Reference: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
"""
import re
from typing import Optional
from urllib.parse import parse_qs

_QR_CODE_PATTERN = re.compile(r'^QR-[A-HJ-NP-Z2-9]{6}$')


def parse_install_referrer(raw: str) -> Optional[str]:
    """Extract a QR-XXXXXX code from a Play Install Referrer or clipboard string.

    Args:
        raw: Either a URL-encoded query string (``referrer=QR-XYZ123&...``) or
             a bare code (``QR-XYZ123``).

    Returns:
        The validated code, or None if no match.
    """
    if not raw:
        return None

    if _QR_CODE_PATTERN.match(raw):
        return raw

    try:
        params = parse_qs(raw)
    except Exception:
        return None
    for candidate in params.get("referrer", []):
        if _QR_CODE_PATTERN.match(candidate):
            return candidate
    return None
