"""
Consent capture (W3-16) -- ToS acceptance + 13+ age attestation.

The mobile client sends three OPTIONAL fields on every account-creating
request (``POST /api/v1/auth/register`` and ``POST /api/v1/auth/social-login``):
``terms_accepted``, ``terms_version``, ``age_attested``. Phones on the
2026-09-02 OTA (97b5f15) send none of them.

Two flags, both default OFF and read PER CALL (``strict_optional_auth_enabled``
idiom, auth_routes.py) so Railway can flip them without a restart:

* ``ENABLE_CONSENT_PERSIST``  -- write ``terms_accepted_at`` / ``terms_version``
  / ``age_attested_at`` into the ``users`` insert. Needs migration 038 applied.
* ``ENABLE_CONSENT_REQUIRED`` -- reject an account creation that carries no
  complete acceptance with 400 ``TERMS_ACCEPTANCE_REQUIRED``. Needs the client
  half on phones (OTA) first, or every registration from an old phone is refused.

The two reads are independent on purpose: PERSIST can go on the day 038 is
applied; REQUIRED waits for the OTA.

``TERMS_VERSION`` must equal ``SmartCompareApp/src/services/consent.ts`` and the
``last_updated`` of ``GET /api/v1/legal/terms_of_service`` (pinned by
tests/test_consent_capture_w3_16.py::test_b12). Bump them together.
"""
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import HTTPException

TERMS_VERSION = "2026-03-26"

TERMS_ACCEPTANCE_REQUIRED = "TERMS_ACCEPTANCE_REQUIRED"
TERMS_ACCEPTANCE_REQUIRED_MESSAGE = "Please accept the Terms and confirm you are 13 or older."

_TRUTHY = ("true", "1", "yes", "on")


def consent_persist_enabled() -> bool:
    """True iff ``ENABLE_CONSENT_PERSIST`` is on (default OFF, read per call)."""
    return os.getenv("ENABLE_CONSENT_PERSIST", "false").strip().lower() in _TRUTHY


def consent_required_enabled() -> bool:
    """True iff ``ENABLE_CONSENT_REQUIRED`` is on (default OFF, read per call)."""
    return os.getenv("ENABLE_CONSENT_REQUIRED", "false").strip().lower() in _TRUTHY


def consent_from_fields(
    terms_accepted: Optional[bool],
    terms_version: Optional[str],
    age_attested: Optional[bool],
) -> Optional[Dict[str, str]]:
    """The consent record for a request, or ``None`` when it is incomplete.

    Complete means BOTH attestations are literally ``True`` and a non-empty
    terms version was sent. The version is recorded as sent (what the user
    actually saw), not coerced to ``TERMS_VERSION``.
    """
    if terms_accepted is True and age_attested is True and terms_version:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "terms_accepted_at": now,
            "terms_version": terms_version,
            "age_attested_at": now,
        }
    return None


def consent_columns(consent: Optional[Dict[str, str]]) -> Dict[str, str]:
    """The extra ``users`` insert columns: the record iff PERSIST is on, else ``{}``."""
    if consent and consent_persist_enabled():
        return dict(consent)
    return {}


def consent_rejection() -> HTTPException:
    """400 with the structured detail the error handler unwraps to top level."""
    return HTTPException(
        status_code=400,
        detail={
            "code": TERMS_ACCEPTANCE_REQUIRED,
            "error": TERMS_ACCEPTANCE_REQUIRED_MESSAGE,
        },
    )
