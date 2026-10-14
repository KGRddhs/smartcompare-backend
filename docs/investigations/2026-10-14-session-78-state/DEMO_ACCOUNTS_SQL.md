# Review accounts for App Review (session 78, 2026-10-14)

Apple's 2.1 message asks for login credentials. Claude may not create accounts or handle passwords. You create the accounts and type the passwords into App Store Connect yourself. Claude never sees them.

## 1. Create two accounts in the app (on your iPhone, build 1.0.0 (2) from TestFlight)

| Account | Suggested email | Used for |
|---|---|---|
| 1 | `appreview1@getmyez.com` | **Apple's reviewer.** Its email and password go in App Store Connect > App Review Information > Sign-In Information. Never run a comparison on it. |
| 2 | `appreview2@getmyez.com` | **Your screen recording.** You may run comparisons on it. |

For each account:
1. Tap **Sign Up**.
2. Enter the email and a password of 10+ characters with an upper-case letter, a lower-case letter and a digit. Save the password in your password manager. **Never paste it in chat.**
3. Tick the 13+ / Terms box and create the account. No email confirmation is needed, so the address does not have to receive mail.
4. Finish the first-run questionnaire once.
5. Sign out before creating the next account.

## 2. Raise both accounts' limit (Supabase SQL editor, project `qulajmyxdbdkchvecmvc`)

Replace the two emails if you used different ones, then run A, B and C in order.

```sql
-- A. read-only: expect 2 rows, subscription_tier 'free', preferences_completed true
SELECT id, email, subscription_tier, preferences_completed
FROM public.users
WHERE lower(email) IN (lower('appreview1@getmyez.com'), lower('appreview2@getmyez.com'));

-- B. read-only: any live constraint on the column (expect 0 rows)
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.users'::regclass
  AND pg_get_constraintdef(oid) ILIKE '%subscription_tier%';

-- C. raise both: expect exactly 2 rows back, both showing the new tier
UPDATE public.users SET subscription_tier = 'premium'
WHERE lower(email) IN (lower('appreview1@getmyez.com'), lower('appreview2@getmyez.com'))
RETURNING id, email, subscription_tier;
```

**What C changes.** Both accounts get 10 comparisons a day and 70 a month, instead of the free 3 a day and 10 a month (`usage_service.py` TIER_LIMITS). The server reads the tier on every comparison, so it applies immediately.

**Caveats (audit F06):**
- The app shows the new count only after Home remounts. Sign out and back in, or force-quit and relaunch.
- Comparisons run today still count until the UTC day rolls over (03:00 Bahrain time).
- **Deleting an account resets its tier.** Never demonstrate deletion with account 1 or 2. The recording deletes a separate throwaway account.
- Never write the tier name in the App Review notes: the app has no in-app purchase.

If A returns anything other than 2 rows, or B returns a row, stop and send Claude the output.
