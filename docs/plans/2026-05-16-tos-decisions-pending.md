# App Store / Play Store Legal Decisions — Pending

**Status:** Deferred 2026-05-16 — user opted to fill in a later session. ALL 15 items remain "Undecided." The drafter AI (or follow-up session) MUST NOT proceed with legal-doc drafting until every line below has a concrete value.

**Reference:** `docs/plans/2026-05-06-tos-fact-base.md` § DECISIONS REQUIRED (canonical source of truth).
**Memory rule enforced:** Never fabricate legal entity names, addresses, contact emails, or registration numbers (see `feedback_no_fabricated_legal_identifiers.md`).
**Age policy LOCKED:** 13+ general audience, Apple **12+**, Google Play **Teen**. Do NOT enroll in Apple "Kids" or Google "Designed for Families". Confirmed pre-session.

---

## Decisions still required

### Entity & registration
1. **Legal entity / trade name on ToS:** Undecided
2. **Commercial registration number (CR):** Undecided
3. **Official address for legal notices in Bahrain:** Undecided

### Contact emails
4. **Support email:** Undecided
5. **Privacy email:** Undecided
6. **Privacy/deletion request response SLA:** Undecided (default proposal: 30 days)

### Developer accounts
7. **Apple Developer Program account holder + email:** Undecided
8. **Google Play Console account holder + email:** Undecided

### Public URLs
9. **Public-facing website URL:** Undecided
10. **Public privacy policy URL:** Undecided
11. **Public terms of service URL:** Undecided
12. **Public account-deletion URL or in-app path:** Undecided (in-app deletion EXISTS per CLAUDE.md auth flow — needs URL to expose)

### Launch labels
13. **ToS effective date:** Undecided (default proposal: date of publication)
14. **Lawyer review status:** Undecided (per CLAUDE.md: no lawyer involved — reconfirm before publish)
15. **Beta vs production launch label:** Undecided (default proposal: "Beta — early access")

---

## When to revisit

Before any of these triggers:
- First TestFlight build going to non-team testers (Apple requires policy URLs in App Store Connect listing)
- First Play Console internal-testing track release (Google requires same)
- Public landing page goes live at `qaren.app` (privacy + ToS URLs need to exist)
- Anyone outside the founding team is invited to the closed beta

## Action when revisiting (next session)

1. Open this file + `docs/plans/2026-05-06-tos-fact-base.md`
2. User fills in each item with a real value
3. Drafter AI runs synthesis per § Task 10-13 in the fact base
4. Outputs replace stale `app/legal/{privacy_policy,terms_of_service}.md` (currently say "SmartCompare" / "@smartcompare.app" — must be replaced wholesale, not patched)
5. New legal docs published at the URLs from items 10-11
6. App Store / Play Console listings updated with item 9-13 values
