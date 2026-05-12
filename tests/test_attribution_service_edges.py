"""Edge-case coverage for app.services.attribution_service.parse_install_referrer.

Complements tests/test_attribution_service.py (the implementer's 4 happy-path
RED tests). These exercise the parser's defensive boundaries so backend-bcd
can't accidentally regress to a permissive regex or skip url-decode handling.

Coverage target: 100% of `parse_install_referrer` branches.

Test fixtures use ONLY the canonical Bundle A unambiguous alphabet
`[A-HJ-NP-Z2-9]` (no 0/1/I/L/O) so these tests stay GREEN after Task #9
tightens `_QR_CODE_PATTERN` to match `app/api/auth_routes.py` line 16.

Reference: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
"""
from __future__ import annotations

import pytest

from app.services.attribution_service import parse_install_referrer


# ============================================
# Input-validation edges
# ============================================


def test_returns_none_for_whitespace_only():
    assert parse_install_referrer("   ") is None
    assert parse_install_referrer("\t\n") is None


def test_returns_none_for_unicode_garbage():
    """Raw payloads from Play Store can be untrusted bytes — never crash."""
    assert parse_install_referrer("référer=QR-ABCDEF") is None  # bad key
    assert parse_install_referrer("\u0000QR-ABCDEF") is None  # NUL-prefixed bare
    assert parse_install_referrer("referrer=QR-АBCDEF") is None  # Cyrillic 'А'


def test_returns_none_for_very_long_input():
    """A 100 KB malicious blob must not OOM or hang the parser."""
    long_blob = "referrer=" + ("X" * 100_000)
    assert parse_install_referrer(long_blob) is None


def test_returns_none_for_lowercase_bare_code():
    """Bare-code branch is also case-sensitive (defense-in-depth with query branch)."""
    assert parse_install_referrer("qr-abcdef") is None
    assert parse_install_referrer("Qr-Abcdef") is None


def test_returns_none_for_wrong_length_bare_code():
    assert parse_install_referrer("QR-ABCDE") is None   # 5 chars
    assert parse_install_referrer("QR-ABCDEFG") is None  # 7 chars
    assert parse_install_referrer("QR-") is None


def test_returns_none_for_bare_code_with_surrounding_chars():
    """Bare-code regex must anchor — substring matches are forbidden."""
    assert parse_install_referrer("XQR-ABCDEF") is None
    assert parse_install_referrer("QR-ABCDEFX") is None
    assert parse_install_referrer(" QR-ABCDEF ") is None  # untrimmed input


# ============================================
# Query-string edges (the realistic Play Install Referrer shape)
# ============================================


def test_accepts_code_when_other_params_present_first():
    """utm params before referrer must not break extraction."""
    raw = "utm_source=share&utm_medium=link&referrer=QR-ATAUX9&utm_campaign=loop1"
    assert parse_install_referrer(raw) == "QR-ATAUX9"


def test_takes_first_valid_referrer_when_multiple_provided():
    """parse_qs returns referrer=[v1, v2]; we should walk in order and take the
    first that matches the regex (defends against an attacker injecting a
    second decoy referrer to steal credit).

    Codes use only the canonical unambiguous alphabet [A-HJ-NP-Z2-9].
    """
    raw = "referrer=QR-FRSTAB&referrer=QR-SCNDCD"
    result = parse_install_referrer(raw)
    assert result == "QR-FRSTAB"


def test_skips_invalid_referrer_and_returns_next_valid():
    """If referrer[0] is garbage, the parser walks the candidate list and finds
    the next valid entry — this is intentional per the impl's `for candidate
    in candidates` loop."""
    raw = "referrer=garbage&referrer=QR-VALDXY"
    assert parse_install_referrer(raw) == "QR-VALDXY"


def test_returns_none_when_all_referrer_values_invalid():
    raw = "referrer=garbage1&referrer=garbage2&utm_source=x"
    assert parse_install_referrer(raw) is None


def test_returns_none_when_no_referrer_key():
    """A query string with utm-only params has no `referrer` to extract."""
    raw = "utm_source=share&utm_medium=link"
    assert parse_install_referrer(raw) is None


def test_handles_url_encoded_referrer_value():
    """Play Install Referrer payloads arrive URL-encoded.

    `parse_qs` decodes percent-encoding, so `QR%2DABCDEF` (a hyphen-encoded
    code) → `QR-ABCDEF`. This proves we don't double-decode and lose chars.
    """
    raw = "referrer=QR%2DABCDEF"
    assert parse_install_referrer(raw) == "QR-ABCDEF"


def test_handles_plus_as_space_in_query():
    """Standard application/x-www-form-urlencoded treats `+` as space — codes
    with `+` are NOT valid QR codes, so result must be None (not a crash)."""
    raw = "referrer=QR+ABCDEF"  # decodes to "QR ABCDEF" — invalid
    assert parse_install_referrer(raw) is None


# ============================================
# Self-referral / abuse defenses
# ============================================


def test_rejects_code_with_lowercase_in_query_value():
    """Canonical share codes use the unambiguous uppercase alphabet
    `^QR-[A-HJ-NP-Z2-9]{6}$` — mixed-case must fail even inside a query
    value (defense-in-depth with bare-code rejection)."""
    assert parse_install_referrer("referrer=QR-abcdef") is None
    assert parse_install_referrer("referrer=qr-ABCDEF") is None


def test_rejects_code_with_special_chars():
    assert parse_install_referrer("referrer=QR-ABC!FG") is None
    assert parse_install_referrer("referrer=QR-AB CDEF") is None
    assert parse_install_referrer("referrer=QR-AB-CDEF") is None


def test_none_input_is_safe():
    """`raw` may be passed as None when the iOS/Android shim has nothing to
    forward — the parser must not raise on falsy input."""
    assert parse_install_referrer(None) is None  # type: ignore[arg-type]
