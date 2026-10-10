## 1. Summary

- Both legal documents are rewritten from the code truth table, in English and Arabic: the privacy policy (sections 1-16) and the terms of service (sections 1-17). Every fact only the owner can give is a `<PLACEHOLDER:ID>` token, and every open choice is a fork that `scripts/fill_in_legal.py` fills in later.
- All twelve date anchors stay at `2026-03-26` until the fill-in commit (UL3). The twelve are the two route `last_updated` values, the four markdown dates, the four landing dates and both `TERMS_VERSION` constants.
- Exactly one test is red, by design: `tests/test_legal_docs_u8.py::test_t2_no_unresolved_placeholder` (UL3, UG1). Its CI result is information, not a merge signal (UP13).
- **This branch cannot merge yet.** It waits for the owner's inputs, the fill-in commit and every merge gate in section 8.

## 2. Files

Branch `feature/s73-u8-legal`, cut from `origin/main` `1156f03c` (#325); nothing is committed beyond the base yet. `git diff --stat` shows 16 tracked files, 695 insertions and 480 deletions, and the numbers are identical with `--ignore-cr-at-eol`, so no file was rewritten whole. There are 12 new paths. Every file's final sha256 is in `fix_u8-polish_report.json`. On 2026-10-08, before writing this body, all 29 files were hashed again and every hash matched.

Tracked, changed (lines changed per `--stat`):

- `app/legal/privacy_policy.md` (179): the English policy, sections 1-16, replaced in full.
- `app/legal/terms_of_service.md` (129): the English terms, sections 1-17, replaced in full.
- `app/api/legal_routes.py` (35): a `lang` parameter on both legal routes; the two `last_updated` literals are unchanged.
- `landing/privacy.html` (179), `landing/terms.html` (146): the page body is now a generated `legal:begin/end` region, and the `.draft-notice` CSS rule is deleted.
- `landing/ar/privacy.html` (179), `landing/ar/terms.html` (144): the same change, rendered from the Arabic markdown inside the existing `dir="rtl"` page.
- `landing/support.html` (5), `landing/ar/support.html` (5): a new legal region holding the support contact block (UL11).
- `SmartCompareApp/src/screens/LegalScreen.tsx` (66): requests the document with `lang`, caches it per language, links to the web page when loading fails, and clears the screen when the language changes.
- `SmartCompareApp/src/services/api.ts` (4): `LANDING_BASE_URL` at line 24, four lines below `API_BASE_URL` (UG16).
- `SmartCompareApp/src/i18n/en.json` (1), `ar.json` (1): one new key, `legal.error.openWeb`. English: "Open the web version"; Arabic: (Arabic), waiting for native review.
- `SmartCompareApp/__tests__/LegalScreen.test.tsx` (53): RED amendments (UL17, UG15): the endpoint assertions now expect `lang=en`, the cache keys are `_en`, the `i18n.language` mock is stable, and a `requested()` helper was added.
- `SmartCompareApp/__tests__/landing.brand.s69.test.ts` (45): the LEGAL exemption is dropped, so the brand fence now covers the whole legal page. `ADDRESS_COUNTS` drop from 7 to 5 on the four legal pages (UG20), and the docstring is rewritten (UP4).
- `tests/test_legal_routes.py` (4): two assertions at `:81` and `:91` change `"Qaren"` to `"MYEZ"` (UL17).

New:

- `app/legal/privacy_policy_ar.md` (152 lines), `app/legal/terms_of_service_ar.md` (103): the Arabic documents, translated sentence by sentence into Modern Standard Arabic and marked for native review.
- `app/legal/support_contact.md`, `support_contact_ar.md` (3 lines each): the sources for the support region (UL11, A17).
- `app/legal/processors.json` (197): the processor manifest, 17 rows (UL14).
- `scripts/render_legal_landing.py` (308): the landing renderer. Standard library only, pure ASCII (UL1, UG10).
- `scripts/fill_in_legal.py` (609): the fill-in script. Standard library only, pure ASCII (UL9).
- `scripts/legal_variants_u8.json` (188): the alternative texts, 6 forks and 8 clauses, in English and Arabic.
- `tests/fixtures/legal_fill_in_u8.json` (60): the fill-in data file, with every value null.
- `tests/test_legal_docs_u8.py` (1713): 47 test nodes (30 from RED, 17 appended in the fix round), pure ASCII with `\u` escapes.
- `tests/test_legal_docs_u8_polish.py` (692): 68 test nodes (62 from the polish round, 6 from fix P1), pure ASCII.
- `SmartCompareApp/__tests__/legal/legalScreenLang.u8.test.tsx` (325): T10, 32 cases (29 from RED, 3 added in polish: B9 and B10 x2).

Deliberately left unchanged: `app/services/consent_service.py` and `SmartCompareApp/src/services/consent.ts` (their dates move only at the fill-in, UL18); the `aiConsent.*` and `onboarding.s5.*` catalog keys (UL2, UL16); and `tests/test_consent_capture_w3_16.py` (sha `0db52370`; its date literal at `:39` moves at the fill-in, UL17).

## 3. What the documents now say

### Privacy policy

The Arabic file mirrors the English one heading for heading: 16 level-2 and 6 level-3 headings, pinned by T4. One line per section, with the code fact or ruling behind it:

1. **Who we are.** The controller comes from fork `d5_identity`. Variant A, committed inline, is the name, `TRADE_NAME_CLAUSE` and the address; variant B adds the CR number. Contact is `PRIVACY_EMAIL`, followed by the optional `DPO_CONTACT` clause (UP4 A12c; the owner form, UL15).
2. **Summary.** The App compares two products, uses OpenAI and retailer searches, and does not sell data, show third-party ads or track users across apps.
3. **What we collect and why** (3.1-3.6):
   - 3.1 Account: the email, and a password stored only by the sign-in provider, in hashed form. Also the display name, the sign-in method and the acceptance records (the W3-16 consent columns, migration 038). Apple and Google details are deferred to section 5 (C5).
   - 3.2 Comparisons: typed names, pasted links with their page text, and photos (photos are not stored). Also results, search records including their cost, feedback and Contact Us messages.
   - 3.3 Preferences: priorities, budget level, lifestyle tags, brand attitude and preference history (C4). Country is chosen in onboarding, or else set from the device language and the network location (A7: `Step04Country`, and the CF-IPCountry fallback in `auth_routes`). The behaviour profile is never sent to OpenAI.
   - 3.4 Device and use: a one-way device identifier (migration 021), the notification token, notification records (A8: `re_engagement_events.content_payload`), in-app activity, and usage and referral records.
   - 3.5 Security records: sign-in and security events, including the IP address. Records of failed sign-ins keep a one-way hash of the email that was tried.
   - 3.6 Legal basis: the default that applies when counsel has not reviewed the text (C16). Contract covers the account, comparisons (including the OpenAI step), history and security. Consent covers the optional answers, notifications and attribution. The AI permission is described as the one Apple requires. Fork `legal_basis` swaps in `LEGAL_BASIS_COUNSEL` when `counsel_review` is true.
4. **AI (OpenAI).** The item list matches the consent sheet, plus the "similar" cohort patterns (C4; T8's keyword map). The sentence saying name, email and account identifiers are not sent rests on the C3 / U3c fixes (UL2). It also covers the #274 permission sheet and withdrawal at `WITHDRAW_PATH`, which comes from U3b's merged code. Fork `d3_training` (A inline: "we have not opted in") and fork `openai_retention` (the 30-day abuse-log sentence only when `openai_store_pinned` is true) apply here.
5. **Who receives your data.** The 13 recipients named unconditionally (UG7): Supabase, Railway, Upstash, Sentry, OpenAI, Expo, Apple, Google, Serper, Bright Data, Firecrawl, Scrape.do and Cloudflare. Also retailer websites and Google Fonts. Each one is a `processors.json` row, checked by T7a/b/c.
   - Sentry is stated as "stored in the EU (Germany)". VERIFIED by the orchestrator on 2026-10-08 through the Sentry connector: organisation `qaren-rr` has `regionUrl` `https://de.sentry.io` (the EU region).
   - Google shares the name, email and profile picture (A9). Apple shares the email or a private relay address (C5).
   - People who open an invite link can also see the display name (A14, C2). The referral-notification sentence is fork `referral_push_name` (A15).
   - Website visitors: the hosting logs and Google Fonts receive their IP address (C21).
   - The Cloudflare line is plain, unconditional text (UP10). `YOUTUBE_CLAUSE` appears only while `ENABLE_YOUTUBE_SOURCE` is on.
6. **Retailer websites.** Searches go from our servers and carry product terms only. In link mode our servers open the address the user pasted (C8). Product pictures load on the device straight from the publishing site, or from a search engine's image server, so that site receives the device's IP address (A2: `ProductImage.tsx:101`; F5).
7. **Transfers outside Bahrain.** Data goes to the US (OpenAI) and Germany (Sentry), plus `HOSTING_REGIONS_CLAUSE` and `TRANSFER_BASIS` (the contract wording by default, counsel's wording when `counsel_review` is true). Bahrain is written into the text, so `CONTROLLER_COUNTRY` is guarded (A12a).
8. **How long we keep data.**
   - Data linked to the account is kept until deleted and points to section 9; this sentence reads true under both deletion variants (A4, UP2).
   - Usage counters expire within about 32 days (UL8).
   - Sign-in security records linked to the account are kept "as long as your account exists" (A3: the `login_success` and `invite_code_redeemed` rows carry a user id and an IP).
   - Unlinked failed sign-ins and lockouts are kept for `SECURITY_LOG_RETENTION`; anonymous records for `ANON_LOG_RETENTION`. A fixed period is accepted only while the cleanup job is live (A11, UL8).
   - Photos are not stored. Temporary storage expires within 6 hours (derived from the TTLs). Backups follow each provider's schedule.
9. **Deleting your account.** The section is the token `DELETION_SECTION`, filled with one of two variants. D-NEW (migration 043) is the PR #290 paragraph, whose marker sentence is "We keep only a de-identified record". D-OLD states what migration 025 actually does, including the reminder records it keeps. T11 requires the D-NEW marker exactly when `deletion_variant == "043"` (UG3).
10. **Your rights.** Access and a copy within 15 working days; deletion, objection and restriction within 10 working days; no article numbers (C25). Complaints use fork `territories_complaints`: `gcc` (committed inline) names Bahrain's data protection authority and SDAIA; `bahrain` names only Bahrain's authority.
11. **Notifications.** Referral updates and at most one reminder a week, no advertising (C24). `INAPP_NOTIF_CLAUSE` keeps the false wording until #264 ships.
12. **Children.** The App is for ages 13 and over (the locked age policy). `MINORS_CLAUSE` adds the parent-or-guardian sentence when `minors_clause` is true.
13. **Security.**
   - TLS, certificate pinning, sign-in tokens in the Keychain, and an admin secret key (C9).
   - The UF7 Sentry sentence now opens "From our servers" (A1).
   - The App's reports are disclosed separately: the error message, device model, OS and app versions, and recent request addresses, which can include product names while `sentry.ts:37` does not scrub `product_a` and `product_b` (UP1).
   - The App's performance traces are disclosed (F3; `tracesSampleRate` 0.1). The servers' traces record only the model name and token counts. Breaches are notified as the law requires.
14. **Data kept on your device.** The C6 sentence verbatim. Keychain items can survive deleting the App.
15. **Changes to this policy.** The UL6 wording: we update the effective date and publish the new version, with no in-app notice.
16. **Contact.** `PRIVACY_EMAIL` (followed by `DPO_CONTACT`), `SUPPORT_EMAIL` and `POSTAL_ADDRESS`.

### Terms of service

The Arabic file mirrors the English one: 17 level-2 headings (T4).

1. **Agreement and who we are.** The controller comes from fork `d5_identity`. Creating an account or using the App means agreeing to these Terms.
2. **The service.** Reviews and prices come from public sources. Specifications are compiled by AI from search results and, where those say nothing, from the model's general knowledge (A6: the specs prompt falls back to training data while `ENABLE_SPECS_NO_FABRICATION` is off). The App is a decision aid and sells nothing.
3. **Eligibility and your account.** Ages 13 and over, plus `MINORS_CLAUSE`; accurate information; one account per person; no automated sign-ups.
4. **Free use and limits.** 3 comparisons a day and up to 10 a month, after 3 introductory ones (`usage_service.TIER_LIMITS["free"]`: daily 3, monthly 10, lifetime_free 3). No subscriptions or in-app purchases (#255).
5. **Acceptable use.** Seven prohibitions.
6. **AI-generated content and accuracy.** AI can be wrong. Prices may be converted from another currency or out of date ("estimated" was dropped, A5; the Arabic avoids every word the copy policy bans, UG8). Nothing is professional advice.
7. **Retailers and links.** Retailers are third parties, responsible for their own products, prices and terms.
8. **Intellectual property.** The App belongs to `IP_OWNER` "(or are licensed to us)" (UL15).
9. **Smart Decision Referrals.**
   - Up to 3 successful invites per device, for the device's lifetime (migration 023); each earns 5 comparisons, which expire after 7 days. Pinned by `test_terms_referral_section_matches_migration_023_policy`.
   - Abuse signals are named. What others see follows A14 plus fork `referral_push_name`.
   - The "Deep Review credit" sentence is dropped, because nothing consumes that credit (UP5).
10. **Notifications.** As privacy section 11 (C24, `INAPP_NOTIF_CLAUSE`).
11. **Disclaimers.** The App is provided as is. A price we cannot confirm shows as pending (A5: `is_price_showable` excludes estimated prices, and `sourceMethod.ts` bans that wording). Specifications follow A6; reviews and recommendations are AI-written.
12. **Limitation of liability.** Four exclusions, to the extent the law allows.
13. **Suspension, termination and deletion.** The terms variant of `DELETION_SECTION` (043 or old).
14. **Changes to these Terms.** The same no-notice wording as policy section 15.
15. **Governing law and disputes.** `GOVERNING_LAW` sets both the law and the courts.
16. **Apple.** Apple's Licensed Application End User License Agreement also applies.
17. **Contact.** `SUPPORT_EMAIL` and `POSTAL_ADDRESS` (the legal@ address is dropped, C29).

Support pages: "MYEZ is provided by ..." using fork `d5_identity` (A17), then `SUPPORT_EMAIL`.

## 4. The machinery

**Renderer, `scripts/render_legal_landing.py`** (UL1, UG10, B2-B7):

- It renders six sources into six pages: privacy and terms, English and Arabic, plus the two support pages. Each page has exactly one `<!-- legal:begin -->` / `<!-- legal:end -->` pair (measured: 1/1 on all six). Everything outside the region is never touched.
- Supported markdown: `#`/`##`/`###` headings, paragraphs, one-line `- ` list items, `**bold**`, `*emphasis*`, and links whose URL is http(s) or mailto.
- Anything outside that subset raises `LegalRenderError` instead of rendering differently from the App: a numbered, `*` or `+` item, an indented `- ` item, `>`, a `|` row, four or more `#`, a horizontal rule, or a non-item line right after an item (B6). Sources are read as `utf-8-sig`.
- All text is HTML-escaped, and paragraphs before the first `##` get `class="subtitle"`.
- API: `render_markdown`, `render_regions` (pure: reads, never writes), `write_regions` and `stale_regions`.
- Command line: with no arguments it writes all six regions. `--check` exits 1 when a region is stale and 0 when all are fresh. A `LegalRenderError`, including a missing page (B7), exits 2.
- T5 asserts that every committed region is byte-for-byte equal to a fresh in-memory render. The `.draft-notice` rule appears 0 times on all six pages (measured).

**Fill-in, `scripts/fill_in_legal.py`** (UL9, UG3, UP3, UP8, UP12):

- What it does: reads the fixture and the variants file; selects every fork (it finds whichever variant is present, raw or already filled); expands each clause token from its answer; substitutes the remaining placeholders; writes the six markdown sources; re-renders the six regions.
- It is deterministic: a second run with the same data changes nothing. `--dry-run` writes nothing.
- The effective dates are not placeholders. The orchestrator moves the twelve anchors by hand in the fill-in commit.
- Exit codes:
  - 0: success.
  - 2: an answer, flag or required placeholder is null. It prints the missing keys and writes nothing.
  - 3 (`FillInError`): an inconsistency. Writes nothing.
  - 3 (`RenderAfterWriteError`): the renderer failed after the markdown was written; reachable only by an I/O race.
- Refusals, each exit 3 with nothing written:
  - Markup (`< > [ ]`, backtick, `*`) or a line break in a value. `*_COUNSEL` and `*_COUNSEL_AR` keys may span lines and use `*` and top-level `- ` items, as long as every line stays inside the renderer subset (A10, B6).
  - An empty string, except for `HOSTING_REGIONS(_AR)` (F1).
  - A non-empty value that no selected variant uses; the message says "set it null" (UP3, B5).
  - A value or clause answer changed after a fill; the message says to restore the pre-fill markdown from git (B1, F1).
  - `CONTROLLER_COUNTRY` other than "Bahrain"; the message says sections 7 and 10 must be re-drafted first (A12a).
  - A fixed retention period (a digit, Western or Arabic-Indic, or a duration word in English or Arabic) while `RETENTION_CLEANUP_LIVE` is not "true" (A11).
  - `REFERRAL_PUSH_DISPLAY_NAME_ONLY` or `RETENTION_CLEANUP_LIVE` set to anything but "true", "false" or null.
- Before the first write it checks every page's marker pair and renders every filled source (B2).
- How the fill-in commit is produced (UL9, UP6, UP11):
  1. The orchestrator writes the owner's answers and a names-only read of the seven flags into the fixture.
  2. It runs `python scripts/fill_in_legal.py --dry-run`, then the real run.
  3. It moves the twelve anchors and `tests/test_consent_capture_w3_16.py:39` to the publication date, and re-measures `ADDRESS_COUNTS`.
  4. The commit is reviewed by the orchestrator and gets its own adversary.
  5. T2 is green on that commit.

**Variants and forks, `scripts/legal_variants_u8.json`:**

- **Forks** (6; the committed markdown carries the recommended variant inline):
  - `d5_identity`: A inline; covers the privacy, terms and support pages.
  - `d3_training`: A inline. The B variant now ends with the A16 sentence ("governed by OpenAI's terms rather than the 30-day limit below").
  - `openai_retention`: `true` inline.
  - `territories_complaints`: `gcc` inline.
  - `legal_basis`: `false` inline.
  - `referral_push_name`: `true` inline, but `if_null` is "false". **A null answer therefore publishes the broader email-prefix wording.**
- **Clauses** (8; the markdown carries a token that is derived from an answer):
  - `TRADE_NAME_CLAUSE`, `MINORS_CLAUSE`, `YOUTUBE_CLAUSE`, `INAPP_NOTIF_CLAUSE`, `HOSTING_REGIONS_CLAUSE`, `DPO_CONTACT`, `TRANSFER_BASIS`, and `DELETION_SECTION` (privacy and terms, `043` / `old`).
- Every text exists in English and Arabic.
- The `cloudflare_clause` fork was removed (UP10). Two generic mechanisms remain that no fork uses: the `all_end_with` answer form and the one-empty-variant rule (UP11).

**Manifest, `app/legal/processors.json`** (UL14, UG5-UG7):

- 17 rows, each `{id, name_en, name_ar, kind, personal_data, module, hosts, gate_flag}`. All 17 are `personal_data: true` (measured).
- The rows, by id: supabase, railway, upstash, sentry, openai, expo_push, eas_update, apple, google_sign_in, google_fonts, serper, bright_data, firecrawl, scrapedo, cloudflare, youtube, retailers.
- Exactly one row has `kind: retailer`. Its 13 modules include the App module `ProductImage.tsx` (A2, fix Q5).
- `gate_flag` is set only on youtube (`ENABLE_YOUTUBE_SOURCE`). Railway and Cloudflare have empty module lists (UG7).
- T7a: every row's `name_en` must appear in the English policy and its `name_ar` in the Arabic one.
- T7b: an AST scan of URL literals and client constructors in `app/services`. The NOT_PERSONAL allowlist (Frankfurter, the off-clock Zyte seed) gives each entry a reason of at least 40 characters.
- T7c: client probes for `u.expo.dev`, `@sentry/react-native`, `expo-apple-authentication`, `@react-native-google-signin/google-signin` and `getExpoPushTokenAsync`.

**Fixture schema, `tests/fixtures/legal_fill_in_u8.json`** (UL9, UG4, UP12):

- One JSON object. Every key is required; null means not answered; keys starting with `_` are comments; any other unknown top-level key is an error.
- **Top-level answers** (9): `deletion_variant` (`043` | `old`), `territories` (`bahrain` | `gcc`), `counsel_review` (bool), `d3` (`A` | `B`), `d5` (`A` | `B`), `trade_name` (string, `""` for none), `minors_clause` (bool), `openai_store_pinned` (bool), `inapp_notif_clause` (bool, false until #264).
- **`flags`**: exactly 7 names, each `on` | `off`: `ENABLE_YOUTUBE_SOURCE`, `ENABLE_REENGAGEMENT_PUSHES`, `ENABLE_BONUS_EXPIRY_PUSHES`, `ENABLE_FEWSHOT_ROTATION`, `ENABLE_FIRECRAWL`, `ENABLE_SCRAPEDO`, `ENABLE_BRIGHTDATA_FALLBACK`. They are recorded by the orchestrator from a names-only read, never by an agent or the owner.
- **`placeholders`** (34 keys):
  - 21 owner values: `CONTROLLER_NAME`, `POSTAL_ADDRESS`, `PRIVACY_EMAIL`, `SUPPORT_EMAIL`, `CR_NUMBER`, plus `IP_OWNER`, `GOVERNING_LAW`, `WITHDRAW_PATH`, `SECURITY_LOG_RETENTION`, `ANON_LOG_RETENTION`, `HOSTING_REGIONS`, `LEGAL_BASIS_COUNSEL`, `TRANSFER_BASIS_COUNSEL`, each of those eight with an `_AR` twin.
  - 5 answer keys kept as strings under `placeholders`, because the top level is frozen (UP12): `CONTROLLER_COUNTRY`, `RETENTION_CLEANUP_LIVE`, `REFERRAL_PUSH_DISPLAY_NAME_ONLY`, `DPO_CONTACT_DETAILS`, `DPO_CONTACT_DETAILS_AR`. Null is their documented default, so neither T2 nor the script reports them missing (N3).
  - 8 derived keys, always null: `TRADE_NAME_CLAUSE`, `MINORS_CLAUSE`, `YOUTUBE_CLAUSE`, `INAPP_NOTIF_CLAUSE`, `HOSTING_REGIONS_CLAUSE`, `TRANSFER_BASIS`, `DELETION_SECTION`, `DPO_CONTACT`.
- Measured: every value is null today.

**Route `lang` parameter, `app/api/legal_routes.py`** (UL13, UG11, B8):

- The signature is `lang: str = "en"`: a plain default, no `Query()`.
- `_normalise_lang` strips the value, lower-cases it, caps it at 8 characters (`_LANG_MAX_CHARS`) and splits the primary subtag on `-` or `_`. Exactly `ar` serves `<stem>_ar.md`; anything else serves English.
- The legacy paths share the handlers. The `last_updated` literals at `:55` and `:74` are unchanged.
- An Arabic file that does not exist returns the route's existing body, "Content not available."
- T9 pins `ar`, `AR`, ` ar `, `ar-BH` and `ar_SA` (polish file) as Arabic, and `arabic`, `""` and a 64-character value as English. The U13 OpenAPI pin is untouched (adversary B: 141 passed).

**Client half** (UL5, UG14-UG21, UP4 B9/B10):

- `legalLang()` returns `ar` when the i18next language is a string starting with `ar`, and `en` otherwise.
- The request is `api.get(endpoint, { params: { lang } })`.
- Cache key: `legal_cache_${doc}_${lang}`, used for both read and write. The pre-U8 key is never read and is not removed.
- Error state: exactly one `TouchableOpacity` with `accessibilityRole="link"`, labelled `t('legal.error.openWeb')`. It opens `${LANDING_BASE_URL}/[ar/]privacy.html|terms.html` with `Linking.openURL(...).catch(() => {})`.
- A `shownLang` ref clears the shown document when a load starts for another language (B10).
- Landing link: `LANDING_BASE_URL = 'https://qaren-landing-production.up.railway.app'`. It moves together with T10 when `qaren.app` is attached.
- Catalog key `legal.error.openWeb` exists in both catalogs.

## 5. Gates, as measured in the last reports

- **Backend** (`fix_u8-polish_report.json`, 2026-10-08): `[pyt] tag=fix2-backend5 start=2026-10-08 03:13:08 end=2026-10-08 03:13:18 elapsed=10s bound=600s status=FAIL rc=1`. Over five files: 1 failed (`test_t2_no_unresolved_placeholder`), 153 passed, netguard 0.
  - Per file: `test_legal_docs_u8.py` 47, `test_legal_docs_u8_polish.py` 68, `test_legal_routes.py` 11, `test_consent_capture_w3_16.py` 17.
  - `test_landing_fallback_pages_s69.py` contributes 11. That number is derived (154 minus the 143 of the four-file run `[pyt] tag=fix2-backend start=2026-10-08 03:12:33 end=2026-10-08 03:12:42 elapsed=10s bound=600s status=FAIL rc=1`, which showed T2 plus 142 passed), not reported directly.
- **Full jest suite** (jest 29.7.0, last run in the polish round because LegalScreen changed; the polish adversary got the same result): Test Suites: 3 skipped, 360 passed, 360 of 363 total. Tests: 13 skipped, 13 todo, 3536 passed, 3562 total. Snapshots: 42 passed, 0 written.
  - The fix P1 round changed no client byte; my hash check confirms this. It re-ran only the subset: 11 suites, 96 tests passed.
- **tsc** 5.9.3 `--noEmit`: rc 0 (fix P1 round and polish round).
- **eslint** v9.39.4, on the changed files plus `legalScreenLang.u8.test.tsx`: 0 errors and 13 warnings, all present before this branch (polish round and polish adversary). Not re-run in fix P1, because no client byte changed.
- **Mutants per round** (every restore sha-verified):
  - RED backend prototype: 21 killed.
  - RED client prototype: 13 killed, 3 alternative implementation shapes stayed green.
  - GREEN EN: 16 of 16 killed (M17 not run while T2 is red).
  - GREEN AR: 7 of 7.
  - GREEN client: the summary says 23 killed; its list carries 25 KILLED lines. 3 alternative shapes stayed green.
  - Adversary B: 25 of its own, 14 killed, 11 survived.
  - Fix: 17 of 17.
  - Final adversary: 15, 14 killed, MA1b survived.
  - Polish: 63 of 63. These re-kill B's survivors PM01/02/05/06/07 (the B3 pin), CM04 (as C2) and MA1b (as T21). The new B4 and B8 nodes cover PM09-PM11 and PM12, but those mutants were not re-run (NOT VERIFIED). CM08 is still left to the native review.
  - Polish adversary: 19, 12 killed. S1, S2, S3, R1 and T5 survived (P4); S7 and C3 are equivalent mutants.
  - Fix P1: 4 of 4.
- **Comm gate**: an 18-file set (modules referencing `legal_routes|consent_service|render_legal_landing|fill_in_legal`, plus `grep -rl SmartCompareApp tests/`), run at BASE and HEAD.
  - `[pyt] tag=u8-comm-base start=2026-10-07 22:17:43 end=2026-10-07 22:18:44 elapsed=60s bound=1200s status=OK rc=0` and `[pyt] tag=u8-comm-head start=2026-10-07 22:18:53 end=2026-10-07 22:19:33 elapsed=40s bound=1200s status=OK rc=0`: 1628 passed on each side, and `comm -13` is empty.
  - Adversary B measured it again: 1628 = 1628, empty.
  - Re-run by the orchestrator on the final bytes (2026-10-08 03:36, the same grep rule now matching 20 files because the two new U8 test files join the set): `[pyt] tag=fable-u8-comm-head start=2026-10-08 03:35:33 end=2026-10-08 03:36:11 elapsed=39s bound=1200s status=FAIL rc=1` = 1 failed (`test_t2_no_unresolved_placeholder`, by design) / 1742 passed; no other failure, so the comm against the base set is empty. `legal_routes.py` is byte-identical since GREEN EN (sha `9755f7ed`).
- **Other checks:**
  - `render_legal_landing.py --check` rc 0.
  - `py_compile` and ruff `E9,F63,F7,F82` clean on every changed `.py`.
  - `git diff --stat` equals `--ignore-cr-at-eol` (16 files, +695/-480, measured again for this body).
  - Credential-shape scan: 0 hits. No `.snap` file and no `.env` in the diff.
  - Fill-in CLI end to end on scratch copies: 13 of 13 (polish). 230 random legitimate answer sets filled with 0 failures (polish adversary). 2048 `plan()` combinations produced 0 false refusals (final adversary).

## 6. Rounds

| Round | When (AST) | Verdict | What it changed |
| --- | --- | --- | --- |
| RED backend | 10-07 19:43-20:21 | 16 RED + 14 PIN at base, each failing for its stated reason | NEW `test_legal_docs_u8.py` (30 nodes); `test_legal_routes.py` :81 :91 changed to MYEZ |
| RED client | 10-07 20:23-20:55 | 29 RED + 7 PIN over 3 files | NEW T10 file (29 nodes); amended LegalScreen and landing.brand tests |
| Fable RED gate | 10-07 21:05 | PASS. Orchestrator re-run: 18 failed / 40 passed backend, 29 failed / 7 passed client | rulings UG1-UG22 |
| GREEN EN | 10-07 21:43-22:21 | U8 file 12 failed / 18 passed (all on the missing Arabic side); routes 11/11; B12 17/17; comm 1628 = 1628 | EN documents, renderer, fill-in, variants, manifest, fixture, route, six regions |
| GREEN AR | 10-07 22:24-22:46 | 1 failed (T2) / 57 passed | AR documents, `support_contact_ar.md`, AR variants, 7 `_AR` keys, 3 AR test constants |
| GREEN client | 10-07 22:49-23:16 | full jest 360 suites / 3533 tests green; tsc rc 0; eslint 0 errors | `LANDING_BASE_URL`, LegalScreen, catalog key, `ADDRESS_COUNTS` 7 -> 5 |
| Adversary A (legal truth) | 10-07 23:19-23:38 | DEFECTIVE: A1 blocking, A2-A4 major, A5-A12 minor, A13-A17 notes | nothing (read-only, scratch fills) |
| Adversary B (engineering) | 10-07 23:41 - 10-08 00:15 | DEFECTIVE: B1 major, B2-B6 minor, B7-B11 notes | nothing (read-only) |
| Fix | 10-08 00:29-00:47 | all five confirmed and fixed; 1 failed (T2) / 85 passed; full jest 3533 | A1-A4 text in EN and AR, B1 post-condition, 17 appended nodes |
| Final adversary | 10-08 ~01:00-01:17 | SOUND_WITH_MINORS: F1-F3 minor, F4-F5 notes | nothing |
| Polish | 10-08 01:38-02:16 | 1 failed (T2) / 147 passed; full jest 3536 | every UP4 and UP8 item in EN and AR; NEW polish test file; 3 client cases; renderer refusals; B10 |
| Polish adversary | 10-08 02:22-03:01 | SOUND_WITH_ONE_MAJOR: P1 major, P2-P5 minor; the findings list carries notes N1-N3 (its verdict line says N1-N5) | nothing |
| Fix P1 | 10-08 03:10-03:13 | 1 failed (T2) / 153 passed | Cloudflare fork removed, so the line is unconditional (UP10); a12b rewritten; 6 nodes appended |

The orchestrator's rulings between the rounds: UP1-UP7 (2026-10-08 01:16), the UP8-UP9 amendment (01:18) and the UP10-UP13 amendment (03:21).

## 7. Stated limits after the last fix

These merge the lists in `fix_u8_report`, `polish_u8_report` and `fix_u8-polish_report`, deduplicated, one line each.

1. The renderer is strict: `render_regions` raises when any of the six sources is missing, and the Arabic pages have no English fallback.
2. A fork can be re-selected after a fill. A derived clause cannot (`DELETION_SECTION`, `MINORS_CLAUSE`, `YOUTUBE_CLAUSE`, `INAPP_NOTIF_CLAUSE`, `TRANSFER_BASIS`, `DPO_CONTACT`); changing its answer exits 3 with the restore-from-git hint.
3. The post-fill checks are substring tests. A changed value that also occurs elsewhere in its language's documents passes (`GOVERNING_LAW` changed to "Bahrain", for example).
4. A `{value}` clause changed to "" is caught only because its non-empty text disappears. An empty variant cannot be checked for presence.
5. Keys without `_AR` are checked against the English documents only, and `_AR` keys against the Arabic ones. The shared keys (`CONTROLLER_NAME`, `POSTAL_ADDRESS`, `PRIVACY_EMAIL`, `SUPPORT_EMAIL`, `CR_NUMBER`) are caught through their English occurrence or the d5 fork, which also covers the support pages.
6. A non-empty value that no selected variant uses is refused ("set it null"), and "" is accepted only for `HOSTING_REGIONS(_AR)`. This changes behaviour for `CR_NUMBER` under d5 A and for `*_COUNSEL` with `counsel_review` false.
7. D-NEW is the PR #290 paragraph with the spec's deletion path, and the clause that depends on the PRECHECK branch is dropped (UP5). If the PRECHECK lands in branch A, the text therefore over-discloses a de-identified stub that is in fact removed.
8. D-OLD tells the truth about migration 025 but reads badly, by design. It lists the reminder records, and section 3.4 lists notification records.
9. The policy assumes U3c (or its fold into U3b) and `store=False` at publication:
   - The referral sentence follows `REFERRAL_PUSH_DISPLAY_NAME_ONLY`: null or "false" publishes the email-prefix wording.
   - The OpenAI retention sentence follows `openai_store_pinned`.
   - "We have not opted in" is true only once OpenAI organisation data sharing is off.
10. The UF7 sentence now covers only our servers; the App's reports and the App's performance traces are disclosed separately. UF7's two remaining limits are not stated in the policy: the `redis://` fallback puts cache keys into breadcrumbs (production uses the REST client), and the paths of unmatched routes are kept verbatim.
11. The App sentence keeps "which for a comparison can include the product names" until `sentry.ts` scrubs `product_a`, `product_b` and `url` (CLIENT-TRUTH).
12. App exception values are sent raw except for token shapes; the policy calls them "the error message". The device and OS fields come from SDK defaults and were not measured on a device. Whether the native SDK adds the device name with `sendDefaultPii` false is NOT VERIFIED, which is why the text says "set up not to include".
13. The pictures sentence covers `ProductImage.tsx` (9 render sites) and, generically, a search engine's image server; the retailer manifest row lists no hosts (one class). Whether production serves Google thumbnails is NOT VERIFIED.
14. Linked security rows are kept "as long as your account exists" because no job expires them; if migration 044 or #296 ever expires them, the line must change. `SECURITY_LOG_RETENTION` covers only the unlinked failed-sign-in and lockout rows.
15. Railway logs "can record" the requester's IP and the requested address. Railway's retention and its client-IP logging are NOT VERIFIED.
16. "Expire within 6 hours" is derived from the T28/T29 TTLs (the longest is `home:savings`, 6 h).
17. The landing chrome outside the regions hard-codes support@qaren.app on all six legal and support pages and on both index pages. `SUPPORT_EMAIL` appears only inside the regions.
18. `?lang=ar` with a missing Arabic file returns "Content not available."; there is no English fallback.
19. The renderer refuses markdown outside its subset (rc 2 for `--check`, rc 3 for the fill-in). It still accepts a paragraph line followed directly by an item, mis-nested inline emphasis, and `#` inside heading text.
20. A `TRANSFER_BASIS_COUNSEL` value written as a list renders glued into its section 7 paragraph, with rc 0 (P5).
21. Placeholder values may not contain `< > [ ]`, backtick, `*` or line breaks. `*_COUNSEL` and `*_COUNSEL_AR` keys may span lines and use `*` and top-level `- ` items within the renderer subset.
22. B2 is fixed: markers and filled sources are checked before the first write. A renderer failure in `write_regions` after the markdown writes (an I/O race only) exits 3 as `RenderAfterWriteError`. That branch, the renderer-load failure branch and the source-missing branch of `_check_pages` have no test node.
23. The fix, polish and fix P1 nodes are coupled to code:
    - A1 parses the query rung of `sentry.ts`.
    - A2 asserts the remote `Image` source in `ProductImage.tsx`, and fails by design if pictures are ever proxied.
    - A4 reads `migrations/025`.
    - The polish and fix P1 nodes run the real fill-in and variants files on temp copies.
24. `CONTROLLER_COUNTRY` accepts only null or "Bahrain" (case- and space-insensitive); "Kingdom of Bahrain" is refused. Sections 7 and 10 hard-code Bahrain.
25. A fixed retention period means a digit (Western or Arabic-Indic) or a duration word in English or Arabic, and is refused unless `RETENTION_CLEANUP_LIVE` is "true". The check is word-based: "a fortnight" and "a decade" pass, and an Arabic no-fixed-period wording that contains a listed word is refused (fail-closed).
26. `DPO_CONTACT_DETAILS` and `_AR` are independent, so the English and Arabic texts can diverge (P2). The clause says "data protection officer"; a Bahrain data protection guardian would be called an officer.
27. The Cloudflare line in section 5 is unconditional (UP10). If every address and the landing chrome ever move off qaren.app, it over-discloses. Cloudflare Email Routing delivery for qaren.app is NOT VERIFIED.
28. `fill_in_legal.py` keeps two generic mechanisms that no fork uses (the `all_end_with` answer and the one-empty-variant fork rule), and no test exercises them.
29. `test_polish_a12b` was renamed and rewritten, the one exception to the append-only rule (UP10). The polish file now holds 68 nodes.
30. The polish answers live under `placeholders` as strings with null defaults, so neither T2 nor the script forces them; the UP6 checklist does. The fixture comment "test_t2 ... reports every null" is wrong for placeholder-map nulls (N3).
31. With d3 = B and `openai_store_pinned` false, "the 30-day limit below" points at a sentence that is not there (P3).
32. Invite-link viewers "can also see" the display name, but the invite landing can hide it (`show_name=False`).
33. The Arabic section 13 wording for "request bodies", (Arabic): the native review chooses between the two candidate forms (A13).
34. `ar_SA` is pinned in the polish file; `AR_LANG_VALUES` in the frozen prefix of `test_legal_docs_u8.py` is unchanged.
35. A rejecting `openURL` is pinned (B9). An untranslated Arabic catalog value (mutant CM08) is guarded only by the native review.
36. LegalScreen clears the shown document when a load starts for another language, and the spinner shows until that load succeeds or fails. There is no guard against a stale response (N2).

Limits from earlier rounds that the three lists above do not restate:

- The Arabic is machine-drafted MSA and must not be published before the native review (D11).
- The T8-ar keyword patterns fit today's Arabic consent copy and must be re-checked if U3b rewrites `aiConsent.body`.
- The shared EN/AR values (name, address, emails, CR number) put Latin text inside Arabic sentences. An `_AR` rendering of the name is a fill-in-time addition (UP5).
- The client sends `ar` only for values starting with `ar`, without lower-casing, so "AR" gives `en`; this is unreachable (UG18).
- In `LegalScreen.test.tsx`, the api mock has no `LANDING_BASE_URL`, so a future test that presses the link would open `undefined/privacy.html`.

## 8. MERGE GATES (all required)

**UL3 (all of them):**

1. The fill-in commit, produced by `fill_in_legal.py`, is reviewed by the orchestrator and by its own adversary (UL9, UP11), and T2 is green on it.
2. Migration 043's POSTCHECK has passed, so `deletion_variant` is `043`. Otherwise use D-OLD (`old`), which is not recommended.
3. U3b is merged: the withdrawal control, with `WITHDRAW_PATH(_AR)` taken from the merged code.
4. U3c, or its fold into U3b, is merged: the referral push shows the display name only (C1), and `store=False` is set on every OpenAI dispatch, with an AST pin (C3).
5. The owner has confirmed that OpenAI organisation data sharing is OFF (D3 = A).
6. The native Arabic review is recorded in this PR body.
7. The landing is redeployed in the same window as the merge.

Also: `AI_CONSENT_VERSION` may stay at 1 only if U3b leaves `aiConsent.title` / `aiConsent.body` untouched; check this again at the gate (UL16). The client Sentry rung (UP1) gates the policy's App sentence, not this branch; the clause stays truthful until it ships.

**UP6 fill-in checklist:**

- Move all twelve anchors to the publication date, together with `tests/test_consent_capture_w3_16.py:39`. Current locations:
  - `app/api/legal_routes.py:55` and `:74`
  - `app/legal/privacy_policy.md:5`, `app/legal/terms_of_service.md:5`, `app/legal/privacy_policy_ar.md:5`, `app/legal/terms_of_service_ar.md:5`
  - `landing/privacy.html:185`, `landing/terms.html:174`, `landing/ar/privacy.html:179`, `landing/ar/terms.html:165`
  - `app/services/consent_service.py:31` and `SmartCompareApp/src/services/consent.ts:12` (the two `TERMS_VERSION` constants)
- Re-measure `ADDRESS_COUNTS` on the six pages after the email placeholders are filled. GREEN client's estimate, if the addresses are @qaren.app: privacy 9, terms 6, support 10, and the same for Arabic. **NOT measured.**
- Record the seven flags from a names-only read.
- Set `openai_store_pinned`, `REFERRAL_PUSH_DISPLAY_NAME_ONLY`, `RETENTION_CLEANUP_LIVE` and `CONTROLLER_COUNTRY` from facts, and `deletion_variant` from the 043 POSTCHECK.
- Record the native review, redeploy the landing, and deploy the backend before the OTA.

**Placeholder-map answers** (`PR_NOTES_POLISH.md`, with the stale Cloudflare line replaced by the fix_u8-polish Q2 text):

- `CONTROLLER_COUNTRY`: "Bahrain". Sections 7 and 10 name Bahrain, so any other value is refused until they are re-drafted.
- `RETENTION_CLEANUP_LIVE`: "true" only once the DEL-FOLLOWUPS cleanup (migration 044, #296) is merged and its Railway cron registered. Until then, `SECURITY_LOG_RETENTION(_AR)` and `ANON_LOG_RETENTION(_AR)` must use no-fixed-period wording.
- `REFERRAL_PUSH_DISPLAY_NAME_ONLY`: "true" only once U3c is on main, and the merge gate requires "true". Null or "false" publishes "your display name or the first part of your email address".
- `DPO_CONTACT_DETAILS` / `_AR`: null (no data protection officer or guardian), or the name and contact, in BOTH languages. The script does not yet enforce the pair (P2).
- The Cloudflare line of privacy section 5 is unconditional (fix P1 amends UP4 A12b). The landing pages publish support@qaren.app outside the legal regions, so email to a qaren.app address passes through Cloudflare whatever `PRIVACY_EMAIL` and `SUPPORT_EMAIL` are, and T7a stays green at the fill-in. If the owner later moves every address AND the landing chrome off qaren.app, revisit the line, the Cloudflare manifest row and T7a together.
- An empty string is accepted only for `HOSTING_REGIONS(_AR)`. Any value that no selected variant uses must be null: `CR_NUMBER` under d5 A, and `*_COUNSEL` while `counsel_review` is false.
- Owner values:
  - `CONTROLLER_NAME`: the exact legal name as on the Apple membership.
  - `POSTAL_ADDRESS`: it is published; a business address or a PO box is acceptable.
  - `PRIVACY_EMAIL`, `SUPPORT_EMAIL`, and `CR_NUMBER` (d5 B only).
  - `IP_OWNER`: "the publisher" until the IP licence exists.
  - `GOVERNING_LAW`, `WITHDRAW_PATH`, the two retention values, `HOSTING_REGIONS`, and the counsel keys only when `counsel_review` is true.
  - The `_AR` twin of each language-specific value.
- Top-level answers: `deletion_variant`, `territories`, `counsel_review`, `d3`, `d5`, `trade_name`, `minors_clause`, `openai_store_pinned`, and `inapp_notif_clause` (false until #264).

**Native Arabic review** (D11; record the sign-off here). The GREEN AR list (190 entries in `green-ar/native_review_list.json`) predates the fix and polish edits. Those rounds' lists name the later strings: 9 published strings in the fix round and 16 in the polish round. So review the final files rather than the first list alone:

- `app/legal/privacy_policy_ar.md` and `terms_of_service_ar.md`, in full.
- `app/legal/support_contact_ar.md`.
- Every Arabic text in `scripts/legal_variants_u8.json`, including the D-NEW marker sentence, the D-OLD reminders, the d3 B tail, the referral `false` variant and the DPO clause.
- `ar.json` `legal.error.openWeb`.
- Not published, but checked: the three Arabic test constants (`AI_SECTION_KEYWORDS_AR`, `AI_SECTION_NOT_SENT_AR`, `DELETION_DNEW_MARKER_AR`) and the Arabic duration words in `_FIXED_PERIOD`.

Decisions for the reviewer:

- A13's two candidate words for "bodies", (Arabic).
- The renderings of "hashed" and of "tokens".
- The ToS section 9 heading, which follows `profile.notifs.master.title`.
- The catalog labels used in the deletion path.
- The brand form, (Arabic) MYEZ, as in the catalogs (UP5).
- "Officer" or "guardian" in the DPO clause.
- The retailer row's `name_ar`, (Arabic), must stay verbatim in the policy (T7a).

Every Arabic string currently passes the copy-policy node, with 0 banned or scary terms.

**Deploy order (B11).** Deploy the backend (Railway `web`, which serves `GET /api/v1/legal/*?lang=`) BEFORE or TOGETHER WITH the EAS update that ships the new LegalScreen. An older backend ignores `lang` and answers in English, and a new client would cache that answer under `legal_cache_{doc}_ar`. Online fetches heal it; only offline views are affected.

**Landing redeploy.** Merging does not redeploy the landing service; that is the third lever, `railway up landing --path-as-root -s qaren-landing -d` (owner). Run it in the same window as the merge. Until `qaren.app` is attached, the App links to the Railway landing URL.

**Fill-in-time hazards scheduled into the fill-in unit (UP11; stated limits until then):**

- P2: refuse a DPO contact given in one language only.
- P3: refuse d3 = B with `openai_store_pinned` false, or make the A16 tail follow `openai_store_pinned`.
- P5: refuse line breaks in `TRANSFER_BASIS_COUNSEL(_AR)`, which sits inside a paragraph.
- P4: pin the unpinned polish behaviours:
  - Arabic-Indic digits and the Arabic duration words in the fixed-period rule;
  - the `1)` numbered form in the renderer refusal;
  - the a8 assertion on the full Arabic bullet;
  - the case-insensitive suffix compare, which is moot after UP10.
- N2: a guard in LegalScreen against stale responses.
- Fix Q3: remove the two unused generic mechanisms, with a pin that they are refused.
- Also for the fill-in unit (UP5): whether `legal_routes.py` should take `last_updated` from `TERMS_VERSION`, and `_AR` renderings of the name and address if the owner wants them.

## 9. Owner actions that make the sentences true (spec section 5)

1. Apply migration 043, sending the PRECHECK grid back first. This decides `deletion_variant`.
2. Turn OpenAI organisation data sharing OFF (D3 = A), and read the Chat Completions storage default in the dashboard.
3. Confirm the three mailboxes receive mail: send one test message to each.
4. Read the Supabase, Railway and Upstash regions; they become `HOSTING_REGIONS`.
5. Redeploy the landing in the same window as the U8 merge.
6. A controller duty rather than text: a Bahrain PDPA notification or a data protection guardian, if counsel says it applies.

Related, from the rulings:

- Answer the U8 input form, including its three additions in AHMED_TASKS section 2c: the exact legal name as on the Apple membership; whether an IP licence exists (yes / no / will exist); D14 and the DPO / guardian question (UL15).
- Record who answers privacy@ and support@ against the 10 and 15 working-day promises (UL7).
- Decide D3 and D5, and whether counsel reviews the text (`counsel_review`).
- Approve U3c (UL2).

## 10. Follow-ups outside this unit

- **CLIENT-TRUTH (UP1).** The client Sentry query rung (`sentry.ts:37`: `q|query|email|search|text`) must gain `product_a|product_b|url|url1|url2` to match `sentry_service.py:45`, and client exception values should be scrubbed the way the backend scrubs them. After that, the policy's "can include the product names" clause can be dropped; `test_fix_a1` enforces the coupling. C34 (adding Analytics to the SearchHistory purposes in `app.json` and the inventory) is already a line of the same unit (UL4).
- **The pre-U8 cache keys.** `legal_cache_privacy` and `legal_cache_terms` still hold the DRAFT documents on devices that cached them. Nothing reads them; remove them once, on first mount, with their own pinned test (GREEN client Q3, UP4).
- **The device-side Sentry measurement.**
  - What reaches Sentry from a real device: the device name with `sendDefaultPii` false, IP inference, the SDK installation id, and the default breadcrumbs and device context of `@sentry/react-native` 7.2.0. This needs a device or the Sentry dashboard.
  - Adversary A noted that zero react-native Sentry events were recorded in 30 days, so whether mobile reporting works at all is itself unverified.
- **Other follow-ups the rulings name**, to file at this PR where no issue exists:
  - a post-launch "policy updated" notice mechanism (UL6; counsel decides);
  - self-hosting the landing fonts (C21);
  - the retention cleanup of unlinked security logs, anonymous `search_logs` / `user_events` and `content_blocked` rows (#296, migration 044, UL8);
  - `pain_workflow_events` has no writer (UL7);
  - governorate (#284);
  - the "IP not collected" claim rests on the edge, an inventory note (C35, UL4);
  - the notification opt-out (#264), which gates `INAPP_NOTIF_CLAUSE`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
