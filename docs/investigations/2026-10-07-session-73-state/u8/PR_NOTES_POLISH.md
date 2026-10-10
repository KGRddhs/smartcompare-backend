# U8 polish round - lines for the PR body (UP4 B11, GREEN client Q3, UP6 additions)

## Deploy order (adversary B11)

Deploy the backend (Railway `web`, which serves `GET /api/v1/legal/*?lang=`) BEFORE or TOGETHER WITH the EAS update that ships the new LegalScreen. An older backend ignores the unknown `lang` query parameter and answers in English; a new client would then cache that English text (or a DRAFT, if one is still served) under `legal_cache_{doc}_ar`. Online fetches heal it on the next open; only offline views are affected.

## Follow-up, not this unit (GREEN client Q3)

The pre-U8 AsyncStorage keys `legal_cache_privacy` and `legal_cache_terms` (they hold the DRAFT documents) are never read by the new LegalScreen, but they stay on the device. A follow-up may remove them once (for example on the first LegalScreen mount); nothing shows them today.

## Fill-in checklist additions (UP6, from the polish round)

The answers the polish round adds live under `placeholders` in `tests/fixtures/legal_fill_in_u8.json` (the data file's top level is fixed by the schema in `tests/test_legal_docs_u8.py`). Null is each one's documented default, so the fill-in never reports them missing: record them from facts at the fill-in.

- `CONTROLLER_COUNTRY`: `"Bahrain"` (privacy sections 7 and 10 name Bahrain; any other value is refused until they are re-drafted).
- `RETENTION_CLEANUP_LIVE`: `"true"` only once the DEL-FOLLOWUPS cleanup (migration 044) is merged and its Railway cron registered (UL8); until then `SECURITY_LOG_RETENTION(_AR)` / `ANON_LOG_RETENTION(_AR)` must use no-fixed-period wording (a value naming a number or a duration is refused).
- `REFERRAL_PUSH_DISPLAY_NAME_ONLY`: `"true"` only once U3c is on main (the merge gate requires it); null or `"false"` publishes "your display name or the first part of your email address".
- `DPO_CONTACT_DETAILS` / `_AR`: null (no data protection officer or guardian) or the name and contact, shown in privacy sections 1 and 16.
- The Cloudflare line of privacy section 5 is kept only while `PRIVACY_EMAIL` and `SUPPORT_EMAIL` both end in `@qaren.app`. If either does not, the line is removed and `test_t7a_policy_names_every_processor` turns red (its `SPEC_RECIPIENTS_EN` lists Cloudflare unconditionally): amend the Cloudflare manifest row / T7a in the fill-in commit.
- An empty string is accepted only for `HOSTING_REGIONS(_AR)`; any value no selected variant uses must be null.
