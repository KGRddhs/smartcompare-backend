# Rulings S78-LEGAL (binding): personal-data removal, processor categories, strong ToS v2

**Owner ask, 2026-10-14 (verbatim):** "check the policies carefully and deeply several times with the team of agents and remove any data about the team be it personal data or app secrets or backend stuff or apps used that are needed and more importantly our house locations and address should be removed and it should be a strong ToS following apples laws".

**Owner rulings (AskUserQuestion, 02:50 AST):** address = interim now, P.O. Box later; name = keep, Apple spelling; vendors = categories; date = bump now, server side.

**Evidence base:** `runs/legal_exposure_audit_wf_5cc660fb.json` and `LEGAL_AUDIT_PLAN_S78.md`.

**Unit:** S78-LEGAL.
- Worktree: `C:\Users\SynAckITPC\Documents\AI\sc-s78-legal`.
- Branch: `feature/s78-legal-privacy`, cut from main `4772d492`.

## LR1. Address

The controller's postal address becomes an interim value, set in `tests/fixtures/legal_fill_in_u8.json` (`POSTAL_ADDRESS`) and in its Arabic counterpart:
- EN: "Kingdom of Bahrain (our postal address is available on request at privacy@getmyez.com)"
- AR: the same meaning, in Modern Standard Arabic.

The address may not contain any of the following:
- a block, road, street, avenue, building, flat, house or home number;
- a town, area or village name;
- coordinates.

Whether this applies "on every served legal surface" (legal markdown EN/AR, the API legal routes, the six landing legal regions, `support_contact*.md`) or "in every served file" is decided by LR8 below.

The later swap to a P.O. Box is a one-value re-fill through the same machinery. Design the unit so the swap needs no code change.

## LR2. Controller identity

`CONTROLLER_NAME` = **"Husain Aseeri"**, the App Store Connect account name as displayed on 2026-10-14.
- If the owner reports a different membership spelling, it is a one-value change.
- The Arabic rendering of the name keeps the existing Arabic spelling, unless that spelling distinguishes the two forms. If it does, flag it.

The controller is described as "an individual app developer in the Kingdom of Bahrain, trading as MYEZ", with an Arabic equivalent. Bahrain PDPL Art. 17(1)(a) requires "full name, his field of activity or profession ... and his address".

The name appears ONLY in the identification lines:
- privacy s1 / the controller section;
- the ToS party clause;
- the support page identity line.

No other person's name, no phone number and no personal email address may appear anywhere in served text. Role addresses at getmyez.com (`privacy@`, `support@`) are the only contact routes.

## LR3. Recipients by category

The privacy policy's recipients section (s5) and every other place that names infrastructure vendors describe recipients BY CATEGORY. Only these stay NAMED:
- **OpenAI.** Apple 5.1.2(i) requires naming third-party AI, and the consent sheet names it. Keep the training-use disclosure unchanged in substance.
- **Apple** (Sign in with Apple).
- **Google** (Google Sign-In).
- **"the retailer websites and store search services we query"** (generic).

Rules:
- Gmail becomes "an email provider".
- Add the sentence "We will tell you the names of our service providers on request at privacy@getmyez.com." in EN and AR.
- The international-transfers section lists the destination COUNTRIES or regions that are true per `processors.json`, with no vendor-to-country mapping. Any adequacy or transfer-basis claim must stay no stronger than it is today.
- `app/legal/processors.json` stays the INTERNAL manifest, and the T7 host-scan test keeps using it.
- If any route serves `processors.json` or vendor names publicly, report it in the spec and propose the minimal change. Do not break a client dependency (check SmartCompareApp for any fetch of it).

## LR4. Effective date

All twelve date anchors move together to the merge date. The CLAUDE.md line numbers for the anchors are stale: find the anchors by content.
- Use `2026-10-14` in the unit. The orchestrator re-dates in one mechanical commit if the merge happens on a later day, so make the date a single source if the machinery allows.
- `SmartCompareApp/src/services/consent.ts` TERMS_VERSION moves on main too. It reaches phones only with the first post-approval OTA: no OTA before approval.
- No prior-version archive is published for this change. It is pre-release, only test and review accounts accepted the 2026-10-11 text, and that text contains the home address.

## LR5. Terms of Service v2 (strong, Apple-compliant)

The licence stays Apple's Standard EULA: no custom EULA is uploaded. The ToS is the service terms. Keep the existing section numbering where possible; otherwise renumber consistently in EN and AR and update every cross-reference.

The ToS must contain:
1. **Party clause.** Per LR2, contact by email, no address beyond LR1.
2. **Apple section.** It covers Exhibit B items 1, 3, 4, 5, 6, 7, 9 and 10:
   - the agreement is between the user and the developer, not Apple;
   - Apple has no maintenance or support obligation;
   - the warranty and refund-to-Apple language;
   - product claims are the developer's, not Apple's;
   - third-party IP claims are the developer's;
   - the embargo and restricted-party representation;
   - third-party terms (the user's carrier and data terms);
   - Apple and its subsidiaries are third-party beneficiaries.

   It adds a precedence sentence: the Standard EULA governs the licence to the app software, and these Terms govern the MYEZ service. It contains NO licence-grant wording that would make the ToS read as a custom EULA, and no phone number.
3. **Eligibility.** 13+; users under 18, or under the age of majority where they live, only with a parent's or guardian's permission.
4. **AI and data accuracy disclaimer.**
   - Comparisons are AI-generated from public data and may be wrong, incomplete or out of date.
   - Prices, availability, specifications and ratings must be verified with the retailer.
   - Nothing is professional, medical, health, financial or legal advice. Name the supplements and skincare categories explicitly.
5. **Third-party websites and retailers.** We do not sell products, are not a party to any purchase and do not control third-party sites.
6. **User inputs and the OpenAI exchange.** Consistent with the privacy policy and the consent sheet, word for word in substance.
7. **Acceptable use.**
   - no unlawful, harmful or abusive queries;
   - no automated access, scraping, bots or reverse engineering;
   - no circumvention of usage limits, including multiple accounts or device tricks;
   - no interference with the service;
   - no misrepresenting results as MYEZ statements.
8. **Intellectual property.** The app and its content belong to the developer. Retailer and brand names belong to their owners and are used only to identify products.
9. **Suspension, termination and account deletion.** The in-app deletion path.
10. **Disclaimer of warranties and limitation of liability.**
    - It OPENS with carve-outs: nothing limits liability for fraud, gross negligence, wilful misconduct, death or personal injury, or anything the law does not allow us to limit (Bahrain Civil Code arts 181, 219; art 58 for adhesion contracts).
    - The exclusions apply "to the extent permitted by applicable law".
    - No monetary cap that conflicts with the Standard EULA.
11. **Narrow user indemnity.** It covers only the user's unlawful use or a breach of the acceptable-use rules, to the extent the law allows. Mark it in the spec as subject to counsel.
12. **Changes to the Terms.** A new effective date; material changes are notified in the app or on the website; continued use after notice is acceptance where the law allows.
13. **Governing law.** The Kingdom of Bahrain and its courts, without depriving consumers of mandatory protections where they live.
14. **Boilerplate.** Severability, entire agreement (together with the privacy policy and the Standard EULA), no waiver, and assignment. The developer may assign to a successor entity, for example a company it forms. The user may not assign.
15. **Contact.** Email only; LR1 for the postal line.

The aggregated- or anonymised-statistics clause stays as the owner set it in U8. Its conflict with the in-app "never paid by sellers" copy is an open owner decision (D9). Do not change it in this unit; record it in the spec.

The ToS must not promise any feature the app lacks, and must not contradict the privacy policy, the consent sheet or the App Review notes (`docs/investigations/2026-10-14-session-78-state/NOTES_DRAFT.txt`).

## LR6. Privacy policy completeness

After minimisation, the policy must still carry:
- every Apple 5.1.1(i) element: what is collected, how, every use, the third-party equal-protection confirmation, retention and deletion, consent withdrawal, and the deletion request path, including the in-app path;
- the PDPL rights: access, correction, deletion, objection, and a complaint to the Personal Data Protection Authority;
- children 13+, security, international transfers, changes and contact.

Remove internal detail that is not needed: flag names, cache key names, module names and exact infrastructure.

## LR7. Crawler User-Agent

The User-Agent strings in `app/services/sitemap_discovery_service.py` (~387, used ~411) and `scripts/resolve_search_descriptors.py` (~80) stop carrying any personal email.
- New value: `QarenBot/1.0 (+https://getmyez.com/bot; contact: support@getmyez.com)`. Verify that `landing/bot/` exists and says the same.
- Update any pin.

## LR8. Tests carry no personal data

The RED tests are PATTERN-based and never embed the real address, a personal email, a phone number or any private value. The repo is public.

Denylist patterns over every served legal surface (the legal markdown EN+AR, the landing html files and the generated regions) and over outbound User-Agent strings:
- street-component words followed by digits in EN and AR;
- the town token used in the current address. Reference it via a hash of the normalised token, or via a short generic list of Bahraini town names. Never the house number.
- any `@gmail.com` address;
- `+973` phone shapes.

Positive pins:
- OpenAI is named;
- the Apple section items are present;
- the carve-outs are present;
- the 13+ guardian sentence is present;
- "names of our service providers on request" is present;
- EN/AR parity;
- `render_legal_landing.py --check` is clean;
- the twelve anchors are equal.

## LR9. Machinery only

All legal text goes through the U8 machinery:
- the pre-fill snapshot templates;
- `scripts/fill_in_legal.py` with `tests/fixtures/legal_fill_in_u8.json` and `scripts/legal_variants_u8.json`;
- `scripts/render_legal_landing.py`.

Never hand-edit the generated markdown or the landing regions. The fill-in refuses a changed value after a fill, so the unit restores the pre-fill snapshot and re-fills. Existing U8 / d3c / S77 pins that assert the OLD text are updated deliberately, each one listed in the spec with its reason.

## LR10. Out of scope (recorded, not done here)

- Client strings: an onboarding governorate label that matches a town name is a cohort value, not an address.
- Trimming `/health` internals.
- Masking the docs/state folders: the orchestrator does it in the session docs PR.
- Repo visibility and history rewrite: owner actions.
- PDPA filing, the business mailbox and counsel: owner actions.

## LR11. Deploy

1. Merge with the owner's yes.
2. Railway deploys the API.
3. The orchestrator redeploys the landing from a clean detached checkout of the merge SHA: `railway up landing --path-as-root -s qaren-landing -d`.
4. Verify that `/api/v1/legal/*` (EN and `?lang=ar`) and the six getmyez.com legal pages carry no denylisted pattern.
