/**
 * W3-16 — consent capture: the terms version the user accepts and the
 * payload the account-creating requests carry.
 *
 * Pure module, no imports. `TERMS_VERSION` must equal the backend's
 * `app/services/consent_service.py` TERMS_VERSION and the `last_updated`
 * of `GET /api/v1/legal/terms_of_service` (pinned by
 * tests/test_consent_capture_w3_16.py). Bump all of them together when the
 * redrafted Terms land.
 */

export const TERMS_VERSION = '2026-03-26';

export interface ConsentPayload {
  terms_accepted: true;
  terms_version: string;
  age_attested: true;
}

/** One tick = ToS acceptance AND the 13+ attestation, recorded separately. */
export function buildConsentPayload(): ConsentPayload {
  return {
    terms_accepted: true,
    terms_version: TERMS_VERSION,
    age_attested: true,
  };
}
