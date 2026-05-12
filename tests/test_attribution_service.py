"""Tests for app.services.attribution_service.parse_install_referrer.

Hybrid DIY install-survival: validates code extraction from Play Install
Referrer payloads (Android) and clipboard payloads (iOS).

Reference: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
"""
import pytest

from app.services.attribution_service import parse_install_referrer


def test_parse_install_referrer_returns_code_for_valid_qr():
    referrer_raw = "referrer=QR-ATAUX9&utm_source=share"
    assert parse_install_referrer(referrer_raw) == "QR-ATAUX9"


def test_parse_install_referrer_returns_none_for_invalid_format():
    assert parse_install_referrer("referrer=garbage&utm_source=x") is None


def test_parse_install_referrer_returns_none_for_empty():
    assert parse_install_referrer("") is None


def test_parse_install_referrer_returns_none_for_self_referral_pattern():
    # Defense-in-depth: lowercase codes are invalid per the canonical
    # ^QR-[A-HJ-NP-Z2-9]{6}$ regex shared with RegisterRequest.invite_code.
    assert parse_install_referrer("referrer=qr-abcde2") is None
    assert parse_install_referrer("referrer=QR-abcde2") is None


def test_parse_install_referrer_rejects_confusable_alphabet_chars():
    # Canonical alphabet ^QR-[A-HJ-NP-Z2-9]{6}$ excludes I, O, 0, 1
    # (per auth_routes._INVITE_CODE_RE — L is intentionally allowed since it
    # is distinguishable from 1 in the app's monospace display font).
    # Reject at the earliest layer so bad payloads never reach link_invite_to_user.
    assert parse_install_referrer("referrer=QR-OOO222") is None  # O excluded
    assert parse_install_referrer("referrer=QR-IIIIII") is None  # I excluded
    assert parse_install_referrer("referrer=QR-000022") is None  # 0 excluded
    assert parse_install_referrer("referrer=QR-111122") is None  # 1 excluded
