# S81-11 ADVERSARY -- lens APPREVIEW (Claude Opus 5.5, 2026-11-05 ~11:20-11:40 AST)

Verdict: SOUND (0 blocking, 0 major, 9 minors = stated limits / owner-step wording).

## Verification
- Worktree sc-s81-s11 HEAD 5fcb9fba3b9d78c23289685613c0ae75f4d1199d (verified at start and end); `git status --short` empty at start and end; no .qa-mutation.lock present or created.
- The 8 frozen RED files re-hashed at start and end: all match GC-1 (b30471b3 / f6761781 / 35aa6655 / 48988983 / e4abba60 / 751b24d6 / 573a9c13 / c3e4224c).
- Method: READ-ONLY. This lens needed no mutant and no file edit, so neither a scratch worktree (the client exception forbids one: it would need a junction) nor an in-place byte-copy harness was used. One read-only jest run in place through the junction:
  [jest] tag=s11adv-appreview-copy start=2026-11-05 11:32:09 end=2026-11-05 11:32:19 rc=0 (copy.s11, refusals.s11, refusalsCamera.s11, categoryRow.s11, b3a/honestCopy.b3a, copy-policy: 6 suites, 66 / 66 tests; node v24.11.1, jest 29.7.0 by path)
- No pytest run by this lens (the 23 pins + 6 readers belong to GREEN and the correctness lens).
- Catalog audit by python against base 6869a3e6: en 1,013 -> 1,011, ar 1,013 -> 1,011, parity 0; 15 added / 10 changed / 17 deleted per catalog (the brief's "12 added / 7 changed" is stale wording; the leaf count 1,011 and the PR body's "15 added, 10 changed" agree with the bytes).
- GC-4 diacritics: every new or changed AR value carries no harakat / shadda / tanween except the brand word in referrals.share.messageWithLink (the b3a r31b fence exempts BRAND_AR explicitly). Scary vocabulary: none of the three EN forbidden phrases in any new or changed EN value; none of the AR forbidden pair in any new or changed AR value. No digit in any new or changed EN value (s17 digit-free, R-S11-32).
- [NATIVE READ] (S81_11_NATIVE_READ.md): all 25 added / changed AR keys present with the AR value verbatim; the diacritics note and the month-name rule present. Complete.
- Residual-claim sweep of the EN catalog (electronics / supplement / iPhone / Galaxy / "anything" / N% / N+ / "30 seconds" / "brand or model"): only the category labels (home.categories.*, unreachable while launch = hidden or surfaces OFF) and unrelated keys (Apple sign-in, 55+, 500+ BHD) remain. The fabricated population claims (73 %, the cohort badge, the savings sums, the 2074 counter, the 78 score) are gone from every shipped string and render path.

## Guideline reading of what the OTA ships
- 2.1 completeness: the Home row renders ONE live chip (Fragrances) plus the line "Fragrances only for now" whenever compare is allowed; the coming-soon chips render only when /app/version `surfaces` carries true AND onComingSoon is wired (CategorySelector SURFACE_CHIP_KEYS filter); absent surfaces = no Soon chip, no placeholder. The app is complete for its stated scope. The refusal copy (home.errors.categoryNotLive) promises no date and no feature (R-S11-29 a).
- 2.3 metadata: the in-app copy now under-claims relative to the 1.0.0 ASC description (MINOR-1).
- 4 design: the toast is an inline Text with accessibilityLiveRegion polite (Android) and AccessibilityInfo.announceForAccessibility on iOS only; the Soon chips stay enabled with accessibilityHint = home.categories.comingSoon; the honest price line has numberOfLines 2 in the price slot; the RTL narrow row is a RED row and green.
- 5.1 privacy: no new data collected or sent. The diff adds no trackEvent / posthog / capture / fetch / api.get / api.post / AsyncStorage / SecureStore line; launchSurfaces reads only the already-fetched /app/version body (recordLaunchSurfaces after the json parse in checkForcedUpdate); no event constant (R-S11-27).
- Refusal flows: text (the SSE non-OK arm, the error event, the 200 terminal), link (the axios catch, the 200 success:false) and camera (the 200 action "error" bodies camera_refusal_body / camera_budget_body, app/services/category_gate.py:601-612) all land on the coming-soon copy; the Paywall is reached only on code USAGE_LIMIT (usageService._usageLimitPayload; api.ts:231-234 / :372-386), never on CATEGORY_NOT_LIVE; the CATEGORY_NOT_LIVE Alert calls t(friendlyErrorKey(code)) WITHOUT the count option, so a 429 refusal_daily (retry_after_seconds 3600) never renders seconds. Pinned by refusals.s11 C1 / C2 and the link 429 row (green above).
- Camera reasons: same_identity / category_conflict render the reason sentence + a neutral Back; placeholder_identity / no_evidence / anything else keeps vision_failed (ruled).
- OTA rule UB-R4: no app.json / package / native change in the diff; the PR body's owner step 1 keeps "nothing reaches a phone before approval".

## Blocking
- none.

## Major
- none.

## Minor (each a stated limit or an owner-step wording ruling; none is a rejection-class string or flow)
1. MINOR-1 (2.3 / the OTA-vs-listing window): the 1.0.0 ASC description (ASC_SUBMISSION_PACKET_S76 EN_DESCRIPTION) lists seven categories (electronics, supplements, fragrances, makeup, skin and hair care, fashion, groceries) and the keywords name non-fragrance categories; an approved version's Description and Keywords change only with a new version submission (Promotional Text changes any time). Owner step 4 aligns them "before the 1.0.1 submission", so between this OTA (and, more sharply, the ENABLE_FRAGRANCE_ONLY_GATE flip of step 2) and the 1.0.1 approval the live listing advertises categories the app refuses. An OTA is not reviewed and the 1.0.1 review sees aligned metadata, so not rejection-class; but it is an accuracy gap (2.3.1, and the advertised-purpose condition on downloaded code). Recommended: a stated limit S81-11-L17 (the listing names seven categories until 1.0.1 is approved) and owner-step wording: update Promotional Text at the OTA; submit 1.0.1 with the aligned Description / Keywords / screenshots promptly; prefer the ENABLE_FRAGRANCE_ONLY_GATE flip after the 1.0.1 metadata is live, or record the owner's acceptance of the window in the ledger.
2. MINOR-2 (the 2.3.1 pattern, owner decision 3): `surfaces` is a server switch that turns Soon chips on after review, and owner step 3 keeps it OFF "in every App Review window". Showing something only outside review is the pattern 2.3.1 names; the chips are placeholders, not features, and R-S11-29 rules it; already S81-11-L15. Recommend the L15 text say SF1 turns surfaces on only if the same chips would be acceptable in front of a reviewer.
3. MINOR-3 (2.1 wording): the shipped strings say "coming soon" / "Soon" where R-S11-29 a cited "More categories are coming." as the acceptable form. No date and no feature is promised, so within the ruling; "soon" is the one word a strict reviewer may read as a pending feature. The EN strings are the RED's (GC-9): any change is an orchestrator ruling, not a GREEN defect.
4. MINOR-4 (4 design, copy): the CATEGORY_NOT_LIVE Alert reads title "Fragrances only for now" + body "We compare fragrances for now. ..." ("for now" twice). Cosmetic.
5. MINOR-5 (4 design, narrow width): the as-of / last-seen / listed-on line is numberOfLines 1 inside a card and carries the raw merchant host (S81-11-L12); a long host in AR on a narrow phone truncates the DATE (the line's point) with an ellipsis. Covered by owner step 5 (the TestFlight narrow RTL check); numberOfLines 2 or a host-shortening follow-up is a ruling, not this round.
6. MINOR-6 (accuracy, no year): formatAsOfDate renders month + day only ("Nov 3"); a STORED body from a prior year renders "Listed on Nov 3" with no year. Rare before a year of KB data; a stated limit.
7. MINOR-7 (accuracy): on a LIVE body carrying price.as_of older than 30 days, priceProvenance returns `unknown` even with NO field_status, so the amount is replaced by the not-listed line although a store did list it 31+ days ago ("not listed ... yet" reads slightly untrue for that case). Within the owner's 30-day rule (live-only, R-S11-13) and dormant until ENABLE_KB_FIRST_SERVE; absent as_of keeps today's bytes. Stated limit; the correctness lens owns the OFF proof.
8. MINOR-8 (5.2.1, low risk): onboarding.s1.quote_1 and the two input placeholders name Dior Sauvage / Bleu de Chanel (third-party marks) as examples; nominative use in a comparison app, and the base already named iPhone / Galaxy. Stated limit.
9. MINOR-9 (a11y wording): the Soon chips' accessibilityHint is the one-word badge string rather than a sentence naming "coming soon"; VoiceOver reads "Skincare, button, Soon". Meets R-S11-23 in letter; dormant until surfaces. Stated limit.

## Prove-nothing rows
- none observed for this lens: refusals.s11 asserts navigate NOT called with Paywall in both arities and the exact Alert body on the 429 with retry_after_seconds 3600; categoryRow.s11 renders the absent-surfaces row.

## Not run by this lens (said so)
- No mutant, no pytest, no tsc / eslint, no comm set, no full jest (GREEN and the correctness lens own those; LC-7: the full jest is the final round). No scratch worktree was created (none needed for a read-only lens; the client exception forbids one).
