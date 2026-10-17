# Owner actions, session 79 (2026-10-17): the App Review 2.1 resubmission

Claude cannot do these: they are account-holder, device, credential or legal steps. The order is the order to do them in. Items A1-A2 are new since session 78 and A1 blocks the resubmission outright.

## A. Blockers found in App Store Connect on 2026-10-17

1. **Accept the updated Apple Developer Program License Agreement (Account Holder only).** The Apps page banner reads: "In order to update your existing apps and submit new apps, the Account Holder must review and accept the updated agreement by signing in to their account." Sign in at https://developer.apple.com/account as the Account Holder (Husain Aseeri) and accept it. Until then "Resubmit to App Review" is refused. (Apple sometimes also needs the Paid Applications agreement; the app is free, so only the Program License Agreement should show.)
2. **DSA trader status: no action needed now.** The app is available on 6 storefronts only (Bahrain, Kuwait, Oman, Qatar, Saudi Arabia, United Arab Emirates); the EU is not in the list, so the "Set Up" banner does not block this submission. Decide it only if the availability is ever widened to the EU.

## B. The review accounts (on your iPhone, build 1.0.0 (2) from TestFlight)

3. Create review accounts 1 and 2 exactly as in `../2026-10-14-session-78-state/DEMO_ACCOUNTS_SQL.md` section 1 (Sign Up, password 10+ chars with upper, lower and a digit, finish the questionnaire, Log Out). Send Claude the two email addresses, never the passwords.
4. In the Supabase SQL editor run the read-only checks A and B from that file (Claude can run them for you if you prefer), then run C yourself (the tier raise). Expect exactly 2 rows back.

## B2. Three 30-second checks the truth check asked for (before the reply is sent)

4a. **Supabase > Authentication > Providers > Email > "Confirm email"** must be OFF (last read 2026-10-08). The texts say "No email confirmation needed"; if it is ON, tell Claude and the sentence is dropped.
4b. **Railway `web` variables, names only** (your Terminal panel, never pasted into chat): `OPENAI_BASE_URL` must be unset (else the texts' "OpenAI API" is routed elsewhere); `FIRECRAWL_API_KEY` + `ENABLE_FIRECRAWL` and `SCRAPEDO_API_TOKEN` + `ENABLE_SCRAPEDO` present and on (else that provider is dropped from the services list). Recipe: `railway variables --service web --kv | cut -s -d= -f1 | grep -xE 'OPENAI_BASE_URL|FIRECRAWL_API_KEY|ENABLE_FIRECRAWL|SCRAPEDO_API_TOKEN|ENABLE_SCRAPEDO'`.
4c. **ASC App Review contact name**: "Hussain Aseeri" today; the membership and the live legal pages say "Husain Aseeri". Decide the spelling once and tell Claude (it is typed in step 8).

## C. Device dry run (latest iOS, build 1.0.0 (2))

5. Update the iPhone to the latest iOS and install 1.0.0 (2) from TestFlight (redeem the invite email first if TestFlight asks).
6. Dry run with your OWN main account, per `RECORDING_SCRIPT_v2.md` (this folder) section A steps 9-10. Report three results to Claude:
   - Does "Continue with Google" sign you in? (If not, Google Sign-In is removed from reply item 4 and from the Notes SERVICES line.)
   - Does the photo comparison work? (If not, the recording shows Link mode and reply item 1 says so.)
   - Does "iPhone 15 vs Samsung Galaxy S24" show a complete result (prices, Pros & Cons, Specs)?
7. Record the video with the v2 shot list (section B: the optional sheets, the camera order and the no-tap list changed), trim it (section D), move the file to this PC.

## D. App Store Connect (Claude types, you type the credentials)

8. Say "yes, fill App Store Connect". Claude ticks "Sign-in required" and pastes the verified `NOTES_DRAFT_v2.txt` (this folder) (ASC > MYEZ > iOS App 1.0.0 > App Review Information). You type review account 1's email and password into the User name / Password fields yourself. Also decide the Contact Information: it currently reads "Hussain Aseeri", <PHONE>, <PERSONAL_EMAIL>; Apple shows "Husain Aseeri" on the membership. Keep a number Apple can actually call.
9. Say "yes, send". You attach the video to the Resolution Center reply; the reply `REPLY_DRAFT_v2.txt` (signed "The MYEZ team") is sent; then "Resubmit to App Review". Claude re-warms the review pair just before (the price cache lasts 24 h).

## E. Still open from session 78 (not blocking the resubmission)

10. Make the GitHub repo `KGRddhs/smartcompare-backend` private (it was still public on 2026-10-17 02:00). Check Actions minutes, the Railway GitHub integration and branch protection first.
11. GitHub "Keep my email private"; WHOIS privacy for getmyez.com and qaren.app; the Google OAuth consent-screen support email; the Supabase auth sender.
12. P.O. Box; the exact legal-name spelling on the membership; the PDPA Art. 14 notification; the business mailbox; Bahrain counsel points; the IP licence from the second team member.
13. Version Copyright line "2026 Hussain Aseeri" vs the membership spelling.
14. Housekeeping: rotate the keys in `../2026-10-11-session-77-state/OWNER_ACTIONS_S77.md` item 12; delete the production smoke-test accounts; ask web.archive.org to exclude the old legal pages.


---

# UPDATE 2026-10-17 06:50: the audit's ordered sequence supersedes sections A-D above

Full report: `APP_REVIEW_AUDIT_S79.md` (verdict NEW_BUILD_RECOMMENDED: build 2's sign-in screens block screen recording). The build-3 units are in flight under the harness. Your steps, in order (from the report's section 6; items 2-3 can run today on build 2):

1. Account Holder: accept the updated Apple Developer Program License Agreement at developer.apple.com/account; confirm the ASC banner is gone and nothing is pending under Business > Agreements.
2. On the iPhone (latest iOS, build 1.0.0 (2) from TestFlight): start Screen Recording, open MYEZ, check whether "Welcome back." is black on the phone and in the clip, and whether the Email field still takes a tap. Report the result.
3. Device gate on build 2 with your own account: tap Continue with Google, Continue with Apple, and Scan > Open camera > photograph two products > Compare. Also pick Arabic in a fresh questionnaire (account 2) and note whether the app reloads. Report each result; nothing is sent until all pass or build 3 covers the failures.
4. Approve the build 1.0.0 (3) scope (section 3). After it reaches TestFlight, install it and repeat step 2: sign-in and Sign Up must be visible in the recording.
5. Supabase: Authentication > Email > "Confirm email" must be OFF. Send one Forgot Password email to a test account and confirm the link reaches a working reset page or screen.
6. Railway web variables, names only, in your own terminal (never pasted into chat): OPENAI_BASE_URL unset; FIRECRAWL_API_KEY + ENABLE_FIRECRAWL and SCRAPEDO_API_TOKEN + ENABLE_SCRAPEDO present; also whether ENABLE_COMPARISON_ID_ECHO is set.
7. Create review accounts 1 and 2 as in DEMO_ACCOUNTS_SQL.md section 1; finish the questionnaire; log out. Run checks A and B (expect 2 rows, preferences_completed true), then the tier raise C. Log out, sign in once with exactly the stored account-1 values, confirm the Main tabs, log out.
8. Decide D3 again in the light of guideline 5.1.2(i): keep OpenAI organisation data sharing ON (accept the risk) or turn it off (Claude then updates the description, policy, Terms and Notes).
9. Decide the Copyright spelling (recommended: the membership spelling).
10. Confirm, for reply item 6, that MYEZ has no content partnerships and that removal requests to support@getmyez.com will be honoured; decide whether the backend should stop using search-engine images (variant A) or keep them (variant B).
11. If Apple token revocation is in scope: create a Sign in with Apple key (.p8) for com.qaren.app and store the key, key ID and team ID as Railway secrets.
12. Approve the redesigned screenshot set after the section-7 changes; if you want the Arabic localization in this submission, take the Arabic captures (on build 3 if attached) and approve the Arabic listing texts after a truth check.
13. Say "yes, fill App Store Connect": Claude pastes Notes v3, the description, keywords and screenshots and selects build (3); you tick Sign-in required and type account 1's credentials.
14. Record the video on build 3 per RECORDING_SCRIPT_v2 (build number updated); trim; move it to the PC.
15. Say "yes, send": Claude warms the review pair within 2 h; you attach the video; Reply v3 is sent; "Resubmit to App Review". Claude re-warms every 12-24 h until a decision.
16. Before release (not blocking review): the written IP assignment or licence from the second team member; counsel on the Content Rights basis, complaint authorities and the under-18 guardian clause.

---
