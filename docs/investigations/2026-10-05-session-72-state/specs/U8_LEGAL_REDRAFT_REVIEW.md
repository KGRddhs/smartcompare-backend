# U8 legal redraft: adversarial spec review

Reviewer: Opus, session 72, 2026-10-05, 14:05-14:20 AST. Inputs read in full: `U8_LEGAL_REDRAFT_SPEC.md` (sha256 2ac6fa21...) and `U8_INPUT_FORM_AHMED.md` (ec7c4f63...). The code is read-only at main `845ece15` (`sc-s71-u13`, porcelain empty before and after). Before reading the spec tables I built my own inventory from the code. 29 sampled `file:line` claims were checked; 26 match and 3 do not (see C5, C6 and C23). No legal advice is given here. Web claims are marked with their URL and the date 2026-10-05. Working notes: `specs/u8/review/notes.md`.

## Review corrections (BINDING - supersede the body)

1. **C1 (new, high): a referral push tells the inviter who the invitee is.**
   - Evidence: `app/services/referral_service.py:926-929` builds the display string as `invitee.display_name`, else the part of the invitee's email before the `@`, else "A friend". `push_service.send_loop2_push` (`push_service.py:57-78`) puts that string into the push body. The body then goes through Expo and APNs.
   - What the spec missed: the person who invited a user, and Expo, receive that user's name or email prefix. This is not in T17, P7, section 11 or ToS section 9.
   - It also makes onboarding's "What we never share: Your name. Your email." (`en.json:567-568`) FALSE, not just "too broad" as spec C31 says.
   - Ruling needed:
     - (a) Preferred: a small backend change before publication drops the email-prefix fallback (use `display_name`, else "A friend"). Assign it with C31 (see Q2).
     - (b) Otherwise, policy sections 5 and 11 and the ToS referral section must disclose it.
   - Add truth-table row T31 and contradiction C39 for it.

2. **C2 (new): the invite landing shows the sharer's display name to anyone with the link.**
   - Evidence: `referral_service.py:406` and `:455` return `referrer_display_name` with the stripped comparison. The resolver is anon-executable (`resolve_referral_code`, kept granted to anon by migration 037).
   - T27 and section 5 must say: people you send a comparison or invite link to see your display name and that comparison, without your personalisation.

3. **C3 (new, high): what OpenAI stores is not settled by code.**
   - OpenAI's guide says: "Chat completions are stored by default for new accounts." To disable storage it says: "set `store: false`" (https://developers.openai.com/api/docs/guides/responses-vs-chat-completions, 2026-10-05).
   - The your-data page lists chat completions state as "None, see below for exceptions" (https://developers.openai.com/api/docs/guides/your-data, 2026-10-05).
   - A grep of `app/services` finds no `store=` argument at any call site.
   - So the near-final 4.2 s4 sentence, which names only the 30-day abuse-monitoring logs, depends on account state and not on code.
   - Ruling needed: pass `store=False` at every OpenAI dispatch (through the `guarded_llm_create` chokepoint, or at each of the 15-17 sites), with an AST pin. Put this in U3b (RESEARCH_DIGEST U3b pitfall) or in U8.
   - The fill-in may publish the OpenAI retention sentence only once that pin is on main. The owner's dashboard read in section 5 item 2 then becomes optional.

4. **C4: the AI section leaves out cohort priors and lifestyle tags.**
   - Evidence: `extraction_service.py:2017-2045` adds "COHORT-LEVEL PRIORS (statistical pattern from {n} similar users)". The cohort is chosen from the user's demographic answers. `:1940-1949` sends lifestyle tags (for example `vegan`, `sensitive_skin`, `parent`; `auth_routes.py:184-196`) and brand attitude.
   - Add to 4.2 s4: "and general patterns from people whose survey answers are similar to yours (we never send your age group or gender themselves)". List lifestyle and brand attitude explicitly.
   - Add "similar" to T8's keyword map.
   - The consent copy stays as it is: "including ones suggested from your onboarding answers" covers this, so there is no fence bump.
   - Counsel note: `sensitive_skin` is health-adjacent.

5. **C5: we never receive the Apple name.**
   - `authService.ts:1039` requests the `FULL_NAME` scope. But the Apple sign-in POST body (`authService.ts:1094-1099`) carries only `provider`, `id_token`, `nonce` and consent. `fullName` appears nowhere in `authService.ts`.
   - P12's "email, full name on first sign-in" and T4 are wrong.
   - The policy says: Apple shares your email or private relay address. Google shares your name and email through its sign-in token (whether GoTrue stores the name is NOT VERIFIED).
   - Follow-up, not U8: drop the unused `FULL_NAME` scope (data minimisation).

6. **C6: the device-storage section (4.2 s14) is not true.**
   - It leaves out the Keychain identifiers `device_fp_nonce` and `qaren_device_id_v1`, and `qaren.demographicsPromptState.v1`. That last key is SecureStore (`demographicsTrigger.ts:17,63,73,111`), not AsyncStorage as T26 says.
   - It also leaves out:
     - `@qaren_onboarding_draft_v1`, which holds `age_group`, `gender`, `governorate` and `budget` until they are sent (`onboardingDraft.ts:85-99`);
     - `@qaren_user`;
     - `@qaren_ai_consent_<uid>`.
   - "Deleting the App removes the rest" is not something the code controls. On iOS, Keychain items can survive an uninstall (platform behaviour, NOT VERIFIED on a device).
   - Required near-final text: "The App keeps sign-in tokens and two random device identifiers in your iPhone's secure storage (Keychain), and your profile summary, recent searches, onboarding answers not yet sent, your AI permission record, language settings and a cached copy of this policy in app storage. Signing out removes the sign-in tokens and the profile summary; deleting your account also removes the AI permission record. Items in the Keychain can remain on the iPhone after the App is deleted."

7. **C7: the retention line for usage counters is wrong.**
   - `users.lifetime_comparisons_used` and `last_comparison_at` (RPC at `usage_service.py:514` and `:706`) stay until the account is deleted. Only the Redis daily and monthly keys expire, after 24 h and about 32 d (`:248-262`, `:696-704`).
   - `user_usage` has no writer in `app/` at HEAD (grep). Only legacy rows exist, so fix T16 to say so.
   - Required text: "Daily and monthly counters in temporary storage expire within about 32 days. Your total number of comparisons stays with your account until you delete it."

8. **C8: in link mode we send more than search terms.**
   - In link mode the server fetches the exact URL the user pasted (T12).
   - 4.2 s6 and P15, "contain only product search terms", are overstated. Add: "For comparisons by link, our servers open the page addresses you paste."

9. **C9: the security sentence promises more than the code keeps.**
   - "Error reports are scrubbed of tokens and keys" conflicts with open issues #286 (five unredacted secret shapes) and #311 (exception text still reaches Sentry from five 5xx sites, the error middleware and the cache logs).
   - What is true: backend `send_default_pii=False` and `include_local_variables=False` (`sentry_service.py:314` and `:324`); app `sendDefaultPii: false` (`sentry.ts:237`).
   - Measured in `sc-s70-u4b/SmartCompareApp/node_modules`: `@sentry/react-native` 7.2.0 sets `infer_ip: 'never'` when `sendDefaultPii` is false (`dist/js/client.js:30-33`). This also supports the inventory's "IP not collected" for client Sentry.
   - Required text: "Error reports are set up not to include your name, email or IP address, and we filter common credential formats out of them."

10. **C10: the Support URL page is spec C37, but no unit owns it.**
    - `landing/support.html` (and its AR twin) is a mailto hand-off with no name or address. The ASC Support URL points at it (runbook §6:315; M2).
    - Add `landing/support.html` and `landing/ar/support.html` to the 4.8 files, with CONTROLLER_NAME, POSTAL_ADDRESS and SUPPORT_EMAIL. Keep `landing.brand.s69` ADDRESS_COUNTS (support 9) unless the addresses change.
    - Optional: the footer `© 2026 MYEZ` in `landing/index.html:274` and `ar/index.html:271` becomes `© 2026 <IP_OWNER>`.

11. **C11: T1 does not catch the Arabic DRAFT text.**
    - The AR notices are Arabic (`landing/ar/privacy.html:190,282`; `ar/terms.html:176,266`, measured: مسودة, قالب, مستشار قانوني). T1's English tokens would match them only through the CSS class name.
    - T1 adds those three Arabic tokens for the AR markdown and the AR pages.
    - The `.draft-notice` CSS rule sits in the page `<style>` chrome, outside any generated region (`privacy.html:106`, `terms.html:106`, `ar/*:100`). GREEN deletes it; otherwise T1 stays red forever.

12. **C12: T6 must define the Arabic date format.**
    - The AR anchors read "آخر تحديث: 26 مارس 2026" (`ar/privacy.html:189`, `ar/terms.html:175`).
    - The format rule pins a Gulf month-name table (يناير ... ديسمبر) and T6 parses with it. "Western digits" alone is not a format.

13. **C13: the `lang` parameter must not use a `Query()` default.**
    - `tests/test_consent_capture_w3_16.py:535` calls `legal_routes.get_terms_of_service()` with no arguments. A `lang: str = Query("en")` default would hand the handler a FieldInfo object.
    - Declare `lang: str = "en"` (FastAPI still treats it as a query parameter), normalise it inside the handler, cap its length, and send unknown values to `en`. B12 stays green unedited.
    - Checked: the U13 fixture has 0 legal records, and its OpenAPI pin covers only the ten paid operations and `components`, so adding `lang` does not touch it.

14. **C14: T7 contradicts the YouTube clause, and it is backend-only.**
    - `youtube_service.py:48` has a googleapis host, so T7(b) forces a manifest row. With `personal_data: true`, T7(a) then requires "YouTube" in the policy, while YOUTUBE_CLAUSE is empty when the flag is off.
    - Add a `gate_flag` field. T7(a) applies only when the fill-in data file marks that flag ON (recorded from the names-only read, never read from the environment).
    - Client-side recipients are not covered by a scan of `app/services`: EAS Update (`app.json:268`), Sentry RN (`app.json:252`), Apple and Google sign-in, Expo push token minting. They need rows checked against `SmartCompareApp/app.json` and `src`, or an explicit client allowlist.

15. **C15: `DELETION_POLICY_VARIANT` (T11) does not belong in `app/`.**
    - It has no production reader. Keep it in the fill-in data the tests read.
    - The orchestrator flips it only after POSTCHECK passes, plus the BACKFILL when section 9 c or d is above 0.

16. **C16: the no-counsel legal-basis default contradicts the spec's own source.**
    - 4.2 s3 makes AI processing consent-based.
    - RESEARCH_DIGEST U3b pitfall "Minors": consent needs full legal capacity (Bahrain Art 24(1)(a); KSA IR Art 11(1)(c)) while the app admits 13+. "Prefer contract necessity as the basis for core processing; counsel decides."
    - The no-counsel default therefore uses contract necessity for account, comparison (including the OpenAI step that produces it), history and security. It uses consent only for the optional items: demographics, push and attribution. The in-app AI permission is described as the permission Apple requires.
    - The PR flags this for counsel.

17. **C17: form item 1 cannot fill the placeholders it feeds.**
    - (a) It never asks for the exact legal name string. Under A, that is the name as shown on the Apple Developer membership; it must match the App Store seller byte for byte. The form pre-writes "Hussain Aseeri", taken from the runbook, while project memory spells it "Husain". Under B there is no field for the company name at all.
    - (b) It never asks whether the IP licence or assignment exists, so IP_OWNER (4.4 map) cannot be filled.
    - (c) Item 4 must warn that the address is published on the web and in the app, and accept a business address or PO box.
    - Required change: split item 1 into 1a (exact legal name) and 1b (IP licence: yes / no / will exist before launch).

18. **C18: D14 is not answered.**
    - The form's "Already answered ... Email addresses stay on qaren.app" and spec §0 treat the #257 default as an owner answer. `SESSION_71_STATE.md:20` lists "D3, D5–D14" as open, and the session-69 state doc (:77) says "until decision D14".
    - Add a question:
      - D14: keep `qaren.app` for the addresses (default) or use another domain;
      - confirm the ASC Privacy and Support URLs are the Railway landing URLs until `qaren.app` is attached. RESEARCH_DIGEST pitfall: an ASC URL change ships with the next version, so settle it before submission.
    - Whether mail routing works while the web host returns 522 is NOT VERIFIED (it depends on MX, not the web host).

19. **C19: the OpenAI-entity parenthetical in 4.2 s4 has no source.**
    - "(contracting entity NOT VERIFIED; name it from the owner's OpenAI account terms)" has no placeholder and no form item.
    - Delete it and name the provider as "OpenAI"; counsel may add an entity.

20. **C20: the form omits DPO and guardian status.**
    - RESEARCH_DIGEST pitfalls cover Bahrain Art 14 (prior notification, or a Data Protection Guardian) and KSA IR Art 32 (a DPO; `behavior_profile` may trigger it). CLAUDE.md blocker #2 lists "DPO contact".
    - Add an optional form item: "Have you notified the Bahrain PDPA or appointed a data protection guardian or officer? If yes, give the name and contact." The default is No, and the policy then names the privacy email as the contact.

21. **C21: the web page that carries the policy is itself a data flow.**
    - All landing pages load `fonts.googleapis.com` and `fonts.gstatic.com` (grep, every page) and are served by Railway.
    - Either self-host the two fonts (a landing follow-up), or add one sentence covering website visitors: hosting logs, and Google Fonts receiving the visitor's IP.

22. **C22: no tables in the legal markdown.**
    - LegalScreen renders with `react-native-markdown-display` inside a vertical ScrollView, and `markdownStyles` has no table styles (`LegalScreen.tsx:107-110` plus the style block).
    - The five-column table in 4.2 s3 would be unreadable at phone width and in RTL. Use headings and bullet lists; the generator (Q1) then needs no table renderer.

23. **C23: corrections to the truth table.**
    - T26: fix the key list and storage classes per C6.
    - T16: `user_usage` has no writer.
    - T4/P12: per C5.
    - T23: uvicorn's access log is on (`railway.json:7` has no `--no-access-log`), so every GET request path is logged with its query string. That includes the product names in compare and stream URLs. Change "some queries" to "every GET request path with its query string" (#301). Railway's retention of those logs is NOT VERIFIED.

24. **C24: the notification wording can be true today.**
    - Re-engagement pushes respect `notifications_enabled` (`reengagement_service.py:108`). Referral and bonus pushes do not (#264; `push_service.py` never reads the flag).
    - Required near-final text: "The notification switch in the App stops reminders; to stop all notifications, use your iPhone's Settings." When #264 ships, it becomes the full clause.

25. **C25: the Bahrain Art 18 citation is not verified from the primary text.**
    - On 2026-10-05, `https://www.pdp.gov.bh/en/assets/pdf/regulations.pdf` returned HTTP 403 to a direct fetch. Spec §9's "WAS confirmed" rests on a search snippet.
    - Move it to NOT VERIFIED. The policy cites no article numbers without counsel. The 10 / 15 working-day promises stand as the owner's answers.

26. **C26: the order of work gains items.**
    - Before U8 merges, U3b (or the unit that owns C1/C3) must land: the withdrawal control, `store=False` (C3) and the email-prefix fix (C1).
    - C34 (SearchHistory purposes omit Analytics) changes `app.json` in the binary. It is a precondition of `eas build --profile production`, not a follow-up after it.

27. **C27: `AI_CONSENT_VERSION` stays 1 only on a condition.**
    - The fence (`__tests__/consent/aiConsentVersion.s69.test.ts:32-49`) hashes only `aiConsent.title` and `aiConsent.body` (verified), and the version is 1 (`aiConsent.ts:44`).
    - The version stays 1 only if U3b leaves that copy untouched. If U3b adds withdrawal wording to the sheet (M10), the fence forces version 2, and every user is asked once again.
    - The spec's 4.7 answer must state this condition.

28. **C28: the agent report and the spec number their questions differently.**
    - Spec §8 Q7/Q8 (the inbox owner; `pain_workflow_events` / governorate) are not the report's Q7/Q8 (the U8d cleanup job; the flag read). The spec is authoritative.
    - The report's two questions are answered below as Q9 and Q10.

## Answers to the open questions

- **Q1 (landing generation): accept generation**, on these conditions:
  - a stdlib renderer that writes only a marked region;
  - the markdown subset has no tables (C22) and output is HTML-escaped;
  - AR pages are rendered from `*_ar.md` inside the existing `dir="rtl"` chrome;
  - the `.draft-notice` CSS is deleted from the chrome (C11);
  - T5 compares bytes.
  - The hand-edit fallback is rejected: four pages times every future edit is how today's drift happened.
- **Q2 (C31/C32 owner): U3b.** C31 depends on C1: the "never share your email" line can stay only once the email-prefix fallback is gone. U8 touches neither the `aiConsent.*` keys nor the `onboarding.s5.*` keys.
- **Q3 (order of work): RED and GREEN now, on placeholders, on a branch.**
  - All twelve anchors stay at the base date until the fill-in commit. A placeholder inside `TERMS_VERSION` would break B12 and the consent records.
  - Merge to main only after: the fill-in; 043 POSTCHECK passed; U3b merged; the C1/C3 fixes on main. Then redeploy the landing in the same window.
- **Q4 (C34/C35): yes, file it, as a precondition of the production build** (C26). The ASC labels are filled from the corrected inventory.
- **Q5 (in-app fallback): the landing link on LegalScreen's error state.**
  - No bundled copy.
  - The new `legal_cache_{doc}_{lang}` key also stops the cached DRAFT from being shown offline.
- **Q6 (policy-updated notice): none for 1.0.0.** Before launch only testers and the demo account exist.
  - The policy uses the no-notice wording ("publish the new version in the App and on our website") and must not promise an in-app notice.
  - File a follow-up for changes after launch.
- **Q7 (spec §8, inbox owner): yes.** Record in the runbook who answers privacy@ and support@ against the 10 / 15 working-day promise. Form item 5 tests the delivery.
- **Q8 (spec §8, `pain_workflow_events` / governorate): governorate is already #284.** `pain_workflow_events` having no writer goes in the PR as a note; no new issue.
- **Q9 (report Q7, retention cleanup U8d): accept**, on these conditions:
  - Fold it into #296, widened to cover the unlinked `login_failed` / `brute_force_lockout` rows, anonymous `search_logs` / `user_events`, and `content_blocked` rows (`audit_service.py:67`).
  - It must be merged, with its Railway cron registered by the orchestrator or the owner, before publication when form 10 = B. Otherwise the policy uses the A wording.
- **Q10 (report Q8, prod flag states): agree.**
  - At fill-in time the orchestrator does the names-only read (or exact-line count) of: `ENABLE_YOUTUBE_SOURCE`, `ENABLE_REENGAGEMENT_PUSHES`, `ENABLE_BONUS_EXPIRY_PUSHES`, `ENABLE_FEWSHOT_ROTATION`, `ENABLE_FIRECRAWL`, `ENABLE_SCRAPEDO`, `ENABLE_BRIGHTDATA_FALLBACK`.
  - The result goes into the fill-in data that feeds C14's `gate_flag`. The owner is never asked.

VERDICT: APPROVED_WITH_CORRECTIONS
