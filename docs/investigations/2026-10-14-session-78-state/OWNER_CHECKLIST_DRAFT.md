# Owner checklist: Guideline 2.1 Information Needed (MYEZ 1.0.0 (2))

Do these in order. Nothing here needs a new build, and there must be no OTA to the production branch during review.

## 1. Pre-checks (before you write anything to Apple)
1. **Google Sign-In test (most important)**: on a physical iPhone with TestFlight build 1.0.0 (2), tick the 13+/Terms box and tap **Continue with Google** once, with any Google account.
   - **If it works**: sign out and continue.
   - **If it fails** ("Google sign-in didn't complete"): STOP and tell Claude. The button is always shown in build 2 (LoginScreen.tsx:443-449, RegisterScreen.tsx:424-430), so a reviewer may tap it. Options: fix it in the Google Cloud / Supabase console (no new build needed if the client ids are right), or plan a build 3 that hides it. Also remove "Google Sign-In" from item 4 of the reply and from SERVICES in the notes.
2. **Firecrawl and Scrape.do dashboards**: check that both still have credit and a valid key. If either is exhausted, tell Claude, who will remove it from item 4 and from SERVICES (they are named as fallbacks).
3. **Production health**: open https://getmyez.com and the app once and run one comparison with your own account. If compares fail across the board, fix that first. Recent canaries were often slow or partial (ledger 22:45-23:08).

## 2. Create the two review accounts (in the app, on your iPhone)
1. Sign Up twice, with two emails you control (for example review1@ and review2@ at getmyez.com, or Gmail aliases). Passwords must have 10+ characters with an upper-case letter, a lower-case letter and a digit (LoginScreen.tsx:306-318 rejects others before any network call).
2. For each account, finish the questionnaire (English, Bahrain) and then Log Out. Do NOT run a comparison on either account.
3. Keep the passwords in your password manager. They are never pasted into chat or into any note text.

## 3. Raise their daily limit (Supabase SQL editor, project qulajmyxdbdkchvecmvc)
```sql
UPDATE public.users SET subscription_tier = 'premium'
WHERE email IN ('<review1 email>', '<review2 email>');
SELECT email, subscription_tier, lifetime_comparisons_used FROM public.users
WHERE email IN ('<review1 email>', '<review2 email>');
```
- Expect 2 rows with `premium`. That tier allows 10 comparisons a day and 70 a month (usage_service.py:138-149). It is read from the database on every check, with no cache (usage_service.py:519-541).
- Known cosmetic issue: their header pill shows "0/3 free". Do not tap it. It gets fixed after approval.

## 4. Record the video
Follow the recording script. Use **account 2**, the latest iOS and build 1.0.0 (2) from TestFlight. Do the dry runs on your own main account.
- If the photo dry run fails and you record Link instead, tell Claude, who will change reply item 1 to "a comparison of two product links".

## 5. App Store Connect > MYEZ > iOS App 1.0.0 > App Review Information
1. Tick **Sign-in required**.
2. **User name** = review account 1's email; **Password** = its password. Type both yourself.
3. **Notes**: delete all the old text (it still says "Demo account credentials ... available on request"). Paste the new notes text. It is 3,892 characters, plain ASCII.
4. Contact info: check that the name, phone and email are current. Save.

## 6. Reply in the Resolution Center
1. App Review > the 2.1 message > Reply. Paste the reply text (3,895 characters).
2. Attach the trimmed screen recording. Check that the attachment finished uploading, then send.

## 7. Resubmit
- If ASC shows the build as "Rejected" or "Developer Rejected" with a **Resubmit / Add for Review** button, click it, keeping version 1.0.0 with build 1.0.0 (2), and confirm.
- If the submission is still under review with the message as "Information Needed", sending the reply is enough. Do not cancel the submission.
- Keep manual release ON.

## 8. After sending
- Do not run comparisons on account 1, so its allowance stays free for Apple.
- Watch the Resolution Center and email daily. Keep the phone and the accounts as they are until approval.
- No OTA to the production EAS branch until approval and your manual release.

## Evidence map (for the claims in the texts)
- Sign-in screen first: App.tsx:106, 365-370. "Welcome back.": en.json:1016.
- Sign Up:
  - password rule: RegisterScreen.tsx:194-196;
  - consent box required: RegisterScreen.tsx:218-221, en.json:999;
  - email confirmation OFF: S77 ledger 01:05 entry.
- Questionnaire: 16 screens, from OnboardingFlow.tsx:130-132 and :169-194.
- Type/Scan/Link tabs: HomeScreen.tsx:1001-1036, Scan default at :116.
- Consent sheet:
  - strings: en.json:701-705;
  - stored per user and device: aiConsent.ts:9-17;
  - gates the camera and picker: HomeScreen.tsx:723-740.
- Delete account:
  - EditProfileScreen.tsx:127-139, 259-281;
  - backend: auth_service.py:1008-1023, auth_routes.py:1165-1179;
  - returns to Login: App.tsx:403-405.
- Log Out: ProfileScreen.tsx:296-303, 523-534.
- Limits: usage_service.py:138-149. Paywall has only Done: PaywallScreen.tsx:165-176.
- Bahrain region on every compare:
  - api.ts:258, 681, 824, 971;
  - extraction_service.py:88-95;
  - converted label: en.json:156, price_service.py:306.
- AI processing: privacy_policy.md:63-69. Recipients: privacy_policy.md:75-84.
- Services: openai_service.py:10,33; content_safety_service.py:249-252; serper_service.py:52; firecrawl_service.py:13; scrapedo_service.py:1-13; exchange_rate_service.py:171-175; pushTokenService.ts:81; app.json:226-228, 251-253, 268-269.
- No analytics SDK: S77 ledger 01:00 entry.
- Not advice: terms_of_service.md:40. Ratings never AI-generated: review_service.py:231-279.
- Images not hosted: image_service.py:1-31, privacy_policy.md:95.
- No affiliate links: grep of app/services and SmartCompareApp/src (region report).
- Left out as UNVERIFIED or false:
  - OpenAI model names: production overrides were not read;
  - Bright Data: token expired, breaker tripped;
  - "25+ retailers";
  - link-out to retailers: no caller of openRatingSource;
  - provenance of the drug table.