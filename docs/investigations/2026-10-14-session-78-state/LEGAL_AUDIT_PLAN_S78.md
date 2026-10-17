MYEZ: one change plan to take team data off public surfaces and strengthen the Terms of Service

Repo: sc-docs-70 at main 4772d492. Checked 2026-10-14, read-only. Every personal value is masked in this plan.

## 0. Re-verification

I checked each critical and high finding again before keeping it.

**Confirmed against the repo and the live sites:**
- **Home address (PD-01, PD-02, L1, TOS-01, PP-01).** Two lines each in `app/legal/privacy_policy{,_ar}.md` (:9 and :157) and `terms_of_service{,_ar}.md` (:9 and :103), and one line in `support_contact{,_ar}.md:1`.
  - The landing pages carry it at `landing/privacy.html:188,323`, `terms.html:177,257`, `support.html:210`, `ar/privacy.html:182,317`, `ar/terms.html:168,248` and `ar/support.html:209`.
  - Live GETs today: 2 per page on getmyez.com privacy, terms, ar/privacy and ar/terms; 1 on support and ar/support; 2 on each of `/api/v1/legal/{privacy,terms}` in EN and in `?lang=ar`; 0 on `index.html`.
  - The pre-fill templates `tests/fixtures/legal_prefill_u8/*.md` hold only the `POSTAL_ADDRESS` placeholder at the same lines. The value lives only in `tests/fixtures/legal_fill_in_u8.json:46`; `CONTROLLER_NAME` is at :29, `CR_NUMBER` at :30 and `TRADE_NAME_CLAUSE` at :53.
  - The shipped client: grep finds no address or controller name in `SmartCompareApp/src` or `app.json`.
- **Bahrain PDPL (Law 30/2018), read today from the official English text at https://www.lloc.gov.bh/FullEn/K3018.docx:**
  - Art 17(1)(a) requires "the data controller's full name, his field of activity or profession ... and his address".
  - Art 17(1)(c) allows "Names of the recipients of the data or their categories" and requires a direct-marketing statement.
  - Art 14(1) requires prior notice to the Authority, with an exemption when a Data Protection Guardian is appointed. The notice must include "the name and address of the Data Controller".
  - The Notices and Authorizations Register is open to "Any person ... free of charge". So L4 is confirmed: an address filed with the PDPA is publicly inspectable.
- **Crawler User-Agent (PD-05, S3).** It carries the owner's personal Gmail at `app/services/sitemap_discovery_service.py:387` and `scripts/resolve_search_descriptors.py:80`. The authors fields at `pyproject.toml:6` and `backend/pyproject.toml:6` carry it too.
- **ToS Apple section (TOS-04).** §16 is one sentence (`terms_of_service.md:96-98`).
- **Liability clause (TOS-05).** §12 (`:73-80`) has no carve-outs.
- **Version drift (TOS-06).** Commit `be658fac` (2026-10-12) changed the ToS while the effective date stayed 2026-10-11 (`:5`). `TERMS_VERSION` is 2026-10-11 in `consent.ts:12` and `consent_service.py:31`, and `last_updated` is 2026-10-11 in `legal_routes.py:55,74`.
  - Refinement: the server records whatever version the client sends and never checks it for equality (`consent_service.py:58-64`, `auth_routes.py:591,1151`). So a server-side bump cannot break registration on the build in review. It only makes the recorded version inaccurate.
- **Privacy policy internals (S4, PP-04, PP-06).**
  - 11 infrastructure vendors are named: Supabase, Railway, Upstash, Sentry, Expo, Serper, Bright Data, Firecrawl, Scrape.do, Cloudflare and Gmail. Google Fonts is named as well.
  - "stored in the EU (Germany)" is at :78; the vendor-to-country mapping is at :99; certificate pinning, Keychain and the admin secret-key sentence are at :139.
  - OpenAI appears 13 times. 18 `fonts.googleapis.com` references across the landing pages.
  - T7a (`tests/test_legal_docs_u8.py:20,69-70`) forces every `name_en` in the manifest into the policy.
- **Live backend internals (S6, S7).** `/` returns "SmartCompare API", version 2.1.0, and endpoint keys including admin and docs. `/health` returns `adapter_executor` and the `loop_lag_*` fields.
- **Landing comments (S11, PD-10).** `landing/open.html:16-24` names RT-8 / EXPO-06, `linking.ts` and the Railway host. `open.html:114` holds the first name.
- **Public share view (S5).** `share_routes.py` strips only `metadata.openai`, and its own comment says `total_cost` ships today.
- **Stale client host (S9).** `api.ts:20,24` still points `LANDING_BASE_URL` at the old Railway landing host.

**Refined or dropped:**
- **S7 (Bright Data credential state on /health).** The live `/health` shows only `adapter_executor` and the `loop_lag` fields today. The `brightdata_auth` and pool keys are conditional, so I downgraded this to "can appear".
- **TOS-01 versus L1 and PP-01.** These conflict. TOS-01 says to drop the address from the ToS; that is correct for Apple, because Exhibit B applies only to a custom EULA. But the privacy policy must keep some address (PDPL Art 17(1)(a)). The address can **move** (to a P.O. Box); it cannot be **deleted** from the privacy text. For the ToS it is an owner choice (D3).
- **TOS-03 ("identify the party by reference to the App Store seller").** I rejected this for the privacy policy: Art 17 requires the full name. It is acceptable but unnecessary in the ToS, since the seller name is public anyway.
- **L1 interim "town-level address".** Kept only as an option (D2). The town is the house's locality, so it conflicts with the owner's instruction.

**Not re-verified, kept as reported:**
- The gitleaks admin-key history hit (S2, first 4 characters 9JE8).
- The commit counts that carry the street number (`git log -S` would need the value itself).
- `raw.githubusercontent` returning 200.
- The approximate count of 2,896 commits authored with the personal Gmail.

**Process note.** The SECRETS lens made GETs outside the allowed set (`/openapi.json`, `/docs`, `/robots.txt`, `/api/v1/app/version`, a non-existent route). It also printed a burned third-party guest token (Nasser) into its transcript. Neither is a MYEZ secret, but the harness should treat that transcript as sensitive.

## 1. Owner action, before any text unit (blocks the address swap)

1. **OA-1: get a non-residential address** in the controller's own name: a Bahrain Post P.O. Box, a registered office or a virtual office. Keep the receipt; Apple asks for proof if this address is ever used for DSA trader status. (PD-03, PP-02, L1)
2. **OA-2: confirm the exact legal name** from developer.apple.com > Membership: "Husain" or "Hussain". The fixture comment demands an exact match. PDPL Art 17(1)(a) requires the full name, Art 58(1)(f) penalises misleading data, and DPLA §3.1 requires information to be accurate. (PD-08, L3, PP-08)
3. **OA-3: make `KGRddhs/smartcompare-backend` private.** Before switching, check the Railway GitHub integration, the GitHub Actions minutes on a private plan, and branch protection. (PD-04, PD-06, PD-07, S1, L2, TOS-02, PP-03)

## 2. legal_text_unit (through the U8 machinery; EN and AR together)

**Mechanics:**
- Edit `tests/fixtures/legal_fill_in_u8.json:46` (`POSTAL_ADDRESS`) and :29 (`CONTROLLER_NAME`, only if OA-2 changes it).
- Restore the pre-fill markdown from `tests/fixtures/legal_prefill_u8/`, since `fill_in_legal.py` refuses a refill (REFILL_HINT at :109). Then run `scripts/fill_in_legal.py` and `scripts/render_legal_landing.py`, and check with `render_legal_landing.py --check`.
- Update the pins in the same unit: `tests/test_legal_docs_u8.py` (T7a, UF7 :1482-1528, `SPEC_RECIPIENTS_EN` :782-785), `test_legal_docs_u8_polish.py:582-735`, `test_legal_disclosure_s77.py:106-110,168-172,549-593`, `test_legal_docs_u8_d3c.py:961,1055`, the d3c and s77 fixtures, and `scripts/legal_variants_u8.json` (the `TRANSFER_BASIS` 'false' and `HOSTING_REGIONS_CLAUSE` variants).
- Apply the source-scanning-pins rule from memory: take the union of every test that reads `app/legal` or `landing` by path.

**LT-1 (P0): address swap, first.**
- Privacy §1 and §16: use the P.O. Box (PDPL Art 17(1)(a)).
- ToS §1 and §17, and the support page: either the P.O. Box or role emails only (D3).
- Never a house number, block, road or flat.

**LT-2 (P0): controller identity.**
- The exact legal name, identical on all 6 markdown files and 6 landing pages.
- Add the field of activity, "an individual app developer in the Kingdom of Bahrain", which Art 17(1)(a) requires and which is missing today (PP-07).

**LT-3 (P1): trim internals from the privacy policy.**
- Delete "Administrative functions require a secret key" (`privacy_policy.md:139`).
- Generalise "certificate pinning" and "Keychain".
- Condense the Sentry pipeline sentence at :141 to data categories.
- Condense the deletion mechanics in §9 (:115).
- (S4, PP-06, PP-11)

**LT-4 (P1, depends on D4): recipients as categories.**
- Rewrite §5 as provider categories. Keep **OpenAI** named (Apple 5.1.2(i), the consent sheet `en.json:702`, and the review notes). Keep Apple and Google named for sign-in, which the user chooses.
- Add "names of our service providers on request at privacy@getmyez.com". This also covers the Saudi PDPL Art 13 reading (UNVERIFIED primary text).
- §7: name the countries without the vendor mapping (US, EU/Germany, India, Singapore). Give a lawful transfer basis: Art 13(1)(a) consent and contract necessity, or the Resolution 42/2022 adequacy annex. Today's "required by contract" is not a basis under Art 12 or 13. Counsel should confirm. (PP-05, L9)
- Manifest: add `category_en`, `category_ar` and `public_name` per row in `app/legal/processors.json`, and change T7a to check categories. (PP-17)

**LT-5 (P1): privacy policy strength.**
- An explicit direct-marketing statement (Art 17(1)(c), PP-13).
- Equal-protection wording that does not carve out OpenAI or the mailbox (Apple 5.1.1(i), PP-09). Counsel should review it, and it is only true once the mailbox moves (OA-8).
- Advance notice of material changes (PP-14).

**LT-6 (P1): a strong ToS (v2).** Follow the ToS lens outline, sections 1-23:
- **Apple section.** Exhibit B items 1, 3-7, 9 and 10: the agreement is with us, not Apple; Apple has no support or warranty duty beyond a refund; product and IP claims are ours; an embargo representation; third-party terms; Apple and its subsidiaries are third-party beneficiaries. Add a precedence rule against the Standard EULA. Leave the licence of the app software to the Standard EULA. Do **not** upload a custom EULA (D3). (TOS-04, L7)
- **§12 carve-outs:** fraud, gross negligence, wilful misconduct, death or personal injury, and anything the law forbids limiting. Basis: Bahrain Civil Code art 181, 219 and 58 (WIPO Lex BH083, read from a cached copy) and Exhibit B item 5. (TOS-05)
- **Health paragraph** (Apple 1.4.1 and 1.4.2). (TOS-09)
- **Acceptable use** (TOS-10): add free-limit farming, prompt injection, automated access, resale or competing datasets, photos of people or documents, offensive display names, and a report address. Display names appear on shared invite links, which is user-generated content under Apple 1.2.
- **Inputs licence:** non-exclusive, sublicensable to our providers, ends on deletion except data already shared under OpenAI's programme; define who the owner is. (TOS-11)
- **§13** points to privacy §9 instead of promising full erasure. (TOS-12)
- **§14 changes:** at least 14 days' notice for material changes, and an archive of past versions. (TOS-07)
- **Eligibility:** guardian permission for users under 18, per D8. (TOS-08)
- **§4:** no entitlement to a paid tier or higher limits; we may discontinue features. (TOS-18)
- **Retailer and brand paragraph.** (TOS-15)
- **§9:** refer to "automated abuse checks described in our Privacy Policy" instead of listing the signals. (TOS-14)
- **New §22 General:** entire agreement, severability, no waiver, assignment to a successor such as SYNACKSOFTWARE, force majeure, notices, EN/AR language precedence, and a saving clause for mandatory GCC consumer rights. (TOS-13)
- **Indemnity** per D6.
- **Remove or narrow the right to sell aggregated statistics** (D9, TOS-16).

**LT-7 (P0, with LT-1): date anchors.** Move all twelve together per D5.
- Note that `CLAUDE.md:451` cites stale line numbers: it says `legal_routes.py:30/:47`, but the code is at `:55` and `:74`.
- The RED test must pin all twelve by value, not by line number.

## 3. backend_code

- **BE-1 (P0, small, independent).** Replace the personal Gmail in `_ROBOTS_UA` and `USER_AGENT` with `support@getmyez.com`, or keep only the bot URL. Update the pins: `tests/test_domain_s76.py`, `test_robots_unreadable_ruling.py`, `test_search_descriptor_d3.py`, `tests/fixtures/search_descriptor_d3/SOURCES.json`. Drop the email from both `pyproject.toml` authors entries. (PD-05, S3)
- **BE-2 (P2).** `GET /` returns a minimal status body (S6).
- **BE-2 (P2).** `/health` returns status and message only; move the diagnostics behind the admin key and update the canary runbooks that read `loop_lag_max_60s_ms` (S7, PP-19).
- **BE-2 (P2).** `/admin` returns 404 without the key (S8).
- **BE-3 (P2).** The share view returns an allowlisted public projection with no `metadata` (S5).
- **BE-4 (P3).** Randomise the smoke-test password per run, and replace the ids captured from production in `tests/test_referral_e2e.py:46-49` with synthetic ones (S12).
- **BE-5 (P3).** Ship the migration 044 retention cron, then fill fixed retention periods (PP-15).

## 4. landing_redeploy

The owner runs it from a clean checkout of the merge SHA.

- **LR-1 (P0, same window as LT-1).** Regenerate the six legal regions and redeploy, so getmyez.com matches the API. The backend serves the in-app legal screen after the merge alone; no client update is needed for the text (`LegalScreen.tsx` fetches the API).
- **LR-2 (P2).** Strip the `open.html:15-30` comment and the first-name comment at :114 (S11, PD-10).
- **LR-3 (P3).** Self-host the fonts so Google Fonts drops out of the recipient list (18 references, PP-12).

## 5. client_update (no OTA before approval and the owner's manual release)

- **CU-1.** Bump `consent.ts:12` `TERMS_VERSION` to the new anchor date in the first OTA after approval. Add an in-app notice or re-accept prompt for existing users on material changes (TOS-06).
- **CU-2.** Point `LANDING_BASE_URL` at `https://getmyez.com` (`api.ts:24`, S9). Optionally move the API behind `api.getmyez.com`: re-derive the certificate pins and keep the old host alive for installed builds.
- **CU-3.** Copy fixes: the onboarding line "Not now, not ever" (TOS-17), and "never paid by sellers" if the sale right stays (TOS-16).
- **CU-4.** An in-app "Withdraw AI permission" control backed by a server-side record (PP-10, Apple 5.1.1(ii)).

## 6. asc_metadata (owner, in App Store Connect)

- Keep **Apple's Standard EULA**. A custom EULA triggers Exhibit B item 8: name, address, telephone and email. (L7, PD-09)
- Declare DSA status as **not a trader**, and keep availability to the six GCC storefronts. (L8, PP-20)
- The Copyright line may move from the personal name to the brand (PD-09).
- Check that the App Privacy label, the support URL and the description name no person or address.

## 7. repo_private and the docs PR

- **RP-1.** Private now (OA-3).
- **RP-2.** After the swap: mask the address, phone number, personal Gmails and the second member's surname in `CLAUDE.md` and `docs/investigations/**`. Future ledgers record roles, not names.
- **RP-3 (optional).** Rewrite history with `git filter-repo`, then force-push in coordination with every worktree. GitHub keeps PR refs and cached views, so this needs a GitHub Support purge request (UNVERIFIED wording, docs.github.com). Existing clones and forks cannot be recalled.
- **RP-4.** Set "Keep my email private" on GitHub and commit with the noreply address (PD-06).

## 8. Other owner_action items

- Confirm the PDPA Art 14 notification, or appoint a Data Protection Guardian. Use the P.O. Box in that filing, because the register is public (L4).
- Move support@ and privacy@ to a business mailbox under a DPA (PP-09).
- Confirm the ADMIN_API_KEY rotation by name and date only (S2).
- Delete the production smoke accounts (S12).
- Turn on Sentry "Prevent Storing of IP Addresses" (PP-16).
- Turn on Sentry inbound filters (S14).
- Check web.archive.org for getmyez.com and request exclusion if copies exist.
- Counsel list: whether a P.O. Box meets Art 17; the transfer basis; the precedence clause; Civil Code art 58, 74, 181 and 219; Consumer Protection Law 35/2012; the Saudi PDPL Art 13 and representative duty; minors.