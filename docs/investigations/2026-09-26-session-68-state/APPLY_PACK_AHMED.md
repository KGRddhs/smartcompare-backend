# Ahmed's apply pack — 2026-09-28 (session 68b close)

Nothing is down and nothing needs restoring: production runs current main (`/health` 200 after every merge of the session), the GitHub push trigger deploys `web`, and the session flipped NO flag and touched neither Railway nor Supabase. Every item below needs a credential, a dashboard or a phone this box does not have, and each is written so it can be pasted as-is. Keep every query output next to this file (`docs/investigations/2026-09-26-session-68-state/APPLY_OUTPUTS.md`), as for session 67.

## A. Migration 042 — `public.search_logs.is_synthetic` (W4-13, PR #209) — UNAPPLIED; the hard precondition of `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER`

Merging changed nothing in production; it is a file until you apply it. The file `migrations/042_search_logs_is_synthetic.sql` carries the full BEFORE census, the body and the AFTER check in its header — paste from the file, not from here. In order:

1. **Pause the eval runner** (and any other producer of the 13 probe strings) for the apply — the Supabase SQL editor runs one pasted script in ONE transaction, but at READ COMMITTED a probe row committed between the census and the UPDATE is tagged and not counted (the file explains it).
2. **BEFORE — column check** (must show NO `is_synthetic` column):
   ```sql
   SELECT column_name, data_type, is_nullable
     FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'search_logs'
    ORDER BY ordinal_position;
   ```
3. **BEFORE — census** (run INSIDE step 4's single paste, first): the five-column query from the file header (`a`, `b`, `c`, `a_pull`, `c_pull`). Keep the output; `a_pull` and `c_pull` are the only two comparable to the recorded anchor (`a_pull = 11,724`, `c_pull = 295` from the 2026-09-02 pull) — fewer than the anchor means rows were deleted since (say so); `a > 11,724` or `c > 295` is EXPECTED (pre-June rows and rows written since the pull).
4. **Apply — ONE SQL-editor run (ruling R5 in the file header):** paste, in this order, the UNCOMMENTED five-column BEFORE census query (step 3), then the whole file body (`BEGIN … COMMIT; NOTIFY pgrst, 'reload schema';`), then the first AFTER query `SELECT count(*) FROM public.search_logs WHERE is_synthetic;` — one paste, one run, so the census and the count sit in the same transaction (separate runs let rows written in between break the `(a + b) − c` equality by more than the READ COMMITTED note allows). The column check of step 2 stays a separate read-only run before it. It adds a NULLABLE boolean column with no default, comments it, and runs the ONE-SHOT backfill (the 13 measured probe strings, `created_at < now()`, EXCEPT `'iphone 15 vs galaxy s24'` rows that ran ≥ 10,000 ms — they may be users and stay NULL). No index, policy, grant, function or delete; RLS untouched.
5. **AFTER** (the first query ran inside step 4's paste; the other two are read-only follow-ups):
   ```sql
   SELECT count(*) FROM public.search_logs WHERE is_synthetic;
   SELECT count(*) FROM public.search_logs WHERE is_synthetic AND created_at < TIMESTAMPTZ '2026-06-01 00:00:00+00';
   SELECT count(*) FROM public.search_logs WHERE is_synthetic IS NULL;
   ```
   The first must equal `(a + b) − c` from step 3, or exceed it by the late-committed probe rows only. **Paste back** BEFORE = `a + b`, EXCLUDED = `c`, AFTER, plus `a_pull` and `c_pull`.
6. **Then, in this order and only then:** set `SEARCH_LOG_SYNTHETIC_TOKEN` on `web` AND in the eval runner's environment (a NEW dedicated low-privilege secret; the app never logs it; do not paste it anywhere), then flip `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER=true` on `web`. One minute after the flip: `SELECT count(*) FROM public.search_logs WHERE created_at > <the flip time>` must be > 0 — `log_search` swallows insert errors, so silence would mean a missing column. **Never re-run the backfill after the flip** (forward rows are classified by the caller; a re-run would tag organic users who typed the example pair).
7. **Rollback** (only if needed): turn `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER` OFF FIRST, then `migrations/rollback/042_search_logs_is_synthetic.sql` — it drops the column and discards the classification.

`ENABLE_SEARCH_LOG_TRUTH` (flag 1 of W4-13) needs no migration; the row's activation order is **flag 1 alone → 042 → flag 2 + token → the 1-minute canary**. Flag 1 has no named canary: its flip changes the KPI series (abandoned streams and timeout / moderation terminals start counting as failures), and the bill still says delivered for those terminals until W4-13b (#215) lands.

## B. The next OTA — `eas update --branch preview --clear-cache` from a main at or after `be59d171`

Phones are on EAS preview group `561d2cba` from `ab9442ae` (published 2026-09-24). The ONLY client change merged since is W4-14's client half (one commit, `d3516a40`, measured with `git log ab9442ae..main -- SmartCompareApp`): the dimension labels through the catalog, the referral plural forms, `lang=ar` on the Home compare requests. In order:

1. **Native review of the 51 Arabic dimension labels** — the table is in PR #243's body (`s68b-part3/pr-bodies/prbody_w4_14.md` in this folder) and in `w4-specs/W4_14_UNIT_SPEC.md` §4 A2 (key / EN / AR / reachable); CLAUDE.md's W4-14 client row only records the review requirement; the shipped values are in `SmartCompareApp/src/i18n/ar.json` under `results.dimension.*`. Any change is a tiny PR that edits `ar.json` AND the `AR_LABELS` table in `SmartCompareApp/__tests__/i18n/dimensionLabels.w414.test.ts` (the test pins the 51 values), then the full jest suite. The EN values must NOT change (they echo the backend labels byte-for-byte; a backend CI fence pins that).
2. In `SmartCompareApp`: `npm ls` must be clean (the session-67 rule) before any `eas update`.
3. `eas update --branch preview --clear-cache` from `main` (≥ `be59d171`); record the new group id beside `561d2cba` in the next state doc.
4. **On-device Arabic walkthrough** (the only verification RTL has): the results screen with `lng='ar'` — every rendered dimension label fits `numberOfLines={1}` (the longest reachable label is 21 characters, `sensory`), the runner-up card's point-math rows, the "limited data" row if a backend ever emits one, and an English-app pass showing the labels unchanged.

## C. Flag activation — every one of the fourteen session-68b flags is default OFF; flip NOTHING without its row's preconditions (CLAUDE.md, SESSION 68b block)

Dependency order the rows impose (the details, canaries and stated limits are in the rows):
- W4-13: `ENABLE_SEARCH_LOG_TRUTH` (flag 1) alone first → migration 042 → `SEARCH_LOG_SYNTHETIC_TOKEN` + `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER` (flag 2) → the 1-minute canary (section A).
- `ENABLE_VALUE_DIM_PARTIAL_SIGNAL` (V) and `ENABLE_TIE_IS_NOT_MISSING` (T) (W4-6a) ← the RunnerUpWinsCard empty state on the phone (they reverse the always-render fallback: a sweep pair ships `tradeoffs: []`); then V first, ALONE, watching its log line (the row's activation note); T only after your R7 sign-off on the score movement it causes (`DECISIONS_AHMED.md` item 11). `ENABLE_TIE_IS_NOT_MISSING` is always False while `ENABLE_MISSING_DIM_RENORM` is ON (pinned) — W4-6b (#219) lifts that coupling.
- `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` (W4-7 A) ← W4-6b's order-symmetric tie-break (#219, needs your #101 answer) → `ENABLE_MISSING_DIM_RENORM` → A. `ENABLE_CONFIDENCE_SINGLE_COMPUTATION` (W4-7 B) can go first, alone, with its canary read per price source and per pool state. `ENABLE_FACTCHECK_SHOPPING_KEY` (W4-7 C) after B, in the #107 → C → #106 → #109 order (those three are CLOSED issues that name flag-gated fixes already on main; the order is about flipping them).
- `ENABLE_VERDICT_PROMPT_TRUTH` (W4-11) ← your yes to zero-cons verdicts (`DECISIONS_AHMED.md` item 6) and OpenAI credits; `ENABLE_PRICE_FALLBACK_MAY_DECLINE` independent.
- `ENABLE_CATEGORY_TOKEN_FIX` / `ENABLE_BLOCKLIST_PRECISION_V2` (W4-8): the token fix before the blocklist; #229 (the specs cache keyed on the resolved category) is the rollback hazard to read first.
- `ENABLE_SINGLE_VERDICT_MARGIN` / `ENABLE_SMART_PICK_VERDICT_CAPTION` (W4-12): independent, no precondition; canary the caption flag ALONE (Home copy).
- `ENABLE_ARABIC_VERDICT_OUTPUT` (W4-14): **not before W4-14c (#245)**, the Arabic `max_tokens` measurement, OpenAI credits and the device walkthrough — and Link-mode / camera Arabic users stay English until W4-14b (#244) regardless.

## D. Carried forward, unchanged

- The leaked-key + `ADMIN_API_KEY` rotation (session 65 onward) — still owed; rotation is the only real fix.
- Confirm the #198 Sentry canary (no new issue for an invalid-refresh probe) — session 67's item.
- Still open from the session-67 apply pack (its §B/§C carry the recipes, unchanged): the Supabase Redirect-URL entry `qaren://reset-password` (Dashboard → Authentication → URL Configuration; the precondition of `ENABLE_PASSWORD_RESET_DEEP_LINK`), then `ENABLE_PASSWORD_RESET_DEEP_LINK=true` on `web` after the OTA; `ENABLE_CONSENT_REQUIRED=true` LAST — after the OTA and after `scripts/bundle_d_prod_smoke.py` probes 5, 10, 11 carry the three consent fields; `EXPO_TOKEN`; W3-7's privacy manifest + icons need an `eas build`; the legal review; `railway login` on this box.
- Migrations 035/036 remain unapplied by design; 039 is reserved for the M13-29 RLS migration.
