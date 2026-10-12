# Owner actions after session 77 (MYEZ)

The list is ordered by urgency. Claude cannot do any of these: they are account, DNS, credential, attestation or legal steps.

## While App Review runs (now)

1. **Watch for Apple.**
   - Watch App Store Connect.
   - Check the Gmail inbox that support@getmyez.com forwards to at least twice a day. The review notes promise demo credentials "on request at support@getmyez.com", so Apple may write there.
2. **If Apple asks for a demo account:**
   - Create two accounts in the app: Sign Up, any email, a password of 10+ characters with upper case, lower case and a digit.
   - Go through onboarding once on each. Do NOT run comparisons on them.
   - Tell Claude the two emails; it prepares the read-only checks and the premium SQL (audit finding F06), and you run it in the Supabase SQL editor.
   - Then re-tick "Sign-in required" in App Review Information, type the username and password there, and reply in the Resolution Center.
   - Never paste passwords in chat. Never write "premium" in the notes.
3. **During review, rotate keys only one at a time** (see 12), with a smoke compare after each. A dead backend during review is a 2.1 rejection.

## Before you press Release (after approval)

4. **Supabase:** upgrade to **Pro**. The dashboard showed "No backups" on 2026-10-11. Add a short breach runbook.
5. **DPAs:** accept or download them from Supabase, OpenAI, Sentry, Railway, Upstash, Cloudflare and Expo.
6. **App Store Connect metadata:** confirm the description, promotional text and keywords contain no "authorized", "official" or "Google Play".
7. **Pricing and Availability:** decide on "iPhone and iPad Apps on Apple Silicon Mac" (and Vision Pro). MYEZ has never been run on a Mac; deselect for 1.0, or accept.
8. **GitHub:** make the repository **private**. Check the plan's CI minutes first: about 21 billed minutes per run.
9. **Release:** release 1.0.0 manually. The post-approval update (UI fixes) waits for this.

## PostHog (only when Claude reports the legal unit L live)

Do 10-11 when Claude says unit L is live. Setting a key does nothing until its flag is turned on, which happens at activation, in the order in `NEXT_SESSION_PROMPT_S78.md` section 5.

10. **Create the project.** Create a PostHog project in the **EU cloud** (eu.posthog.com), then:
    - turn **Discard client IP data** ON;
    - keep **Enable exception autocapture** OFF;
    - sign the PostHog DPA;
    - stay on the **free plan** (1-year retention), or tell Claude first, because the policy states 1 year.
11. **Hand over the keys.**
    - Send Claude the **project API key** (starts with `phc_`; it is a public, write-only key) and the **project ID**.
    - Create a **personal API key** with ONLY the `person:write` scope, for automatic deletion when a user deletes their account. Set it yourself in Railway as `POSTHOG_PERSONAL_API_KEY`; never paste it in chat.
    - Confirm `ENABLE_SEARCH_LOG_TRUTH=true` on the Railway `web` service.

## Security and infrastructure (owed since sessions 71-77)

12. **Rotate keys.**
    - Order: the Supabase service key first; then the Upstash token, Serper, Firecrawl, Scrape.do and Zyte keys; then revoke the three old OpenAI keys and the 2026-09-07 transcript-exposed set.
    - Update BOTH Railway services, `web` and `price-warmer`, and redeploy. Run one smoke compare after each rotation.
    - Delete the unused `CLOUDFLARE_API_TOKEN`.
    - Renew the **Bright Data** token; it was 401 on 2026-10-11.
13. **Cloudflare (getmyez.com):**
    - Confirm the apex record is **DNS only** (grey cloud).
    - Delete the `*.getmyez.com` wildcard record.
    - Add DMARC as `_dmarc` with `v=DMARC1; p=none; rua=mailto:privacy@getmyez.com`. Tighten it to quarantine only after checking every sender that uses getmyez.com (Supabase SMTP, any Gmail send-as), and never during App Review.
14. **Sentry:** turn on "Prevent storing IP addresses" on both projects (owed since session 72).
15. **App Store Connect users:** fix Ahmed Jameel's name; it shows a placeholder string. After review, reduce his role from Admin to App Manager, limited to MYEZ.
16. **Optional:** a native Arabic speaker reviews the new Arabic legal sentences (privacy s2/s4/s5/s7/s8/s9, terms s8) and the consent sentence (`2026-10-09-session-75-state/NATIVE_REVIEW_S75.md`).

## Decisions and counsel

These come from `LEGAL_EXPOSURE_REVIEW_S77.md` §3, §7 and §8.

- **Minimum age:** 13+ with guardian wording, or 18+.
- **Published address:** the Hamad Town home address is in the policy. Consider a business address.
- **IP licence:** from Ahmed to Hussain (the app's code and brand).
- **Mailbox:** a controller-owned business mailbox instead of the personal Gmail forward. No DPA covers the Gmail forward today (legal limit L4).
- **Aggregated statistics:** when, if ever, to sell aggregated or anonymised statistics.
- **Terms:** the indemnity clause, and ToS s15/s16 precedence over Apple's standard EULA.
- **Licence extension:** whether to extend the terms s8 licence to OpenAI's own training use (Q2).
- **A GCC lawyer** for the §8 list.

## Decisions Claude took with defaults (tell Claude to change any)

- PostHog: EU cloud.
- An in-app "Share usage analytics" switch, default ON.
- 1-year retention in the policy.
- Automatic PostHog deletion on account deletion.
- The text users type is sent to PostHog with the comparison, and disclosed.
- Session replay later; it needs a new app build.
