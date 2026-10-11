# Session 77 resume prompt (MYEZ App Store submission lane)

Paste this to start session 77. Run under /synack-build-orchestrator: the orchestrator plans and gates, and every workflow agent runs on Opus. Verify the model in the first agent transcript of every launch.

## State at the close of session 76 (2026-10-11 ~05:10 AST)

- **main = eed0f628.** PR #330 (U8 legal, filled) is merged. Session 76 also merged #347 (DOMAIN getmyez.com) and #348 (eas.json submit block).
- **Production backend:** Railway web serves the filled privacy policy and terms (EN + AR, dated 2026-10-11, controller Hussain Aseeri, mailboxes privacy@ and support@getmyez.com).
- **Landing:** redeployed from eed0f628 to the Railway service `qaren-landing`. It is live at https://qaren-landing-production.up.railway.app. All pages, the universal-link file (AASA) and /healthz return 200.
- **getmyez.com still serves the PAUSE Fragrance Study site** (Railway project `getmyez`, service `web`). The domain move is the owner's: the auto-mode classifier refuses DNS and domain changes even with permissionMode = bypassPermissions.
- **Mail:** Cloudflare Email Routing is live on getmyez.com. The MX, SPF and DKIM records are added, and support@ and privacy@ forward to kingzatel@gmail.com. The owner's test mails to both were received.
- **Migration 043** applied (POSTCHECK + BACKFILL 0/0/0). Production flags: ENABLE_PHASE2_RESIDUAL_GUARD and ENABLE_UNIFIED_SEARCH_BOUND are true; canary 7c PASS; the parse flags stay OFF.
- **First store build:** EAS build a3c3e8b5 (1.0.0, build 2) was uploaded with `eas submit` (submission 36725e1d) and processed by Apple ("Ready to Submit"). It is attached to version 1.0.0, and the version page is saved.
- **App Store Connect app record 6772513369, "MYEZ Compare Smart":**
  - Done: App Information (name, subtitle, categories, Content Rights) saved; version 1.0.0 text saved; pricing Free; availability in the 6 GCC countries; age rating set.
  - App Privacy: all 13 data types are saved (linked to the user, no tracking; Other Purposes on Photos or Videos, Other User Content, Search History, Product Interaction and Other Data Types). It is NOT published, and the Privacy Policy URL is empty.
  - Export compliance: ITSAppUsesNonExemptEncryption = false in app.json.

## Remaining, in order

1. **Owner: the getmyez.com domain move** (the classifier blocks the orchestrator).
   1. Railway, project `getmyez`, service `web`, Settings, Networking: delete www.getmyez.com, add pause.getmyez.com, then delete getmyez.com. Its plan allows 2 custom domains.
   2. Railway, project `empowering-enthusiasm`, service `qaren-landing`, Settings, Networking: add getmyez.com and www.getmyez.com.
   3. Cloudflare, getmyez.com, DNS:
      - Point the apex and www CNAMEs at the qaren-landing targets, set to DNS only (grey cloud). Privacy s7 names only the hosting provider and Google Fonts for website visitors; if the records are ever proxied, add Cloudflare to that sentence first.
      - Update the two `_railway-verify` TXT values.
      - Add a pause CNAME (DNS only) and its verification TXT record.
2. **Orchestrator: verify the domain.**
   - `curl -sI https://getmyez.com/privacy.html` must return 200, with no redirect.
   - The AASA at `https://getmyez.com/.well-known/apple-app-site-association` must return 200 application/json.
   - www must redirect to the apex with a 301.
   - Grep `/privacy.html` for "October 11, 2026".
3. **Orchestrator (ASC, after step 2):**
   - App Privacy: set the Privacy Policy URL to https://getmyez.com/privacy.html, then Publish. Publish is an accuracy attestation; the classifier may hand it to the owner.
   - Version 1.0.0: set the Support URL to https://getmyez.com/support.
4. **Owner: two demo accounts** for App Review. Account creation on the live service is prohibited for Claude. The owner pastes the credentials into App Review Information; never into chat.
5. **Orchestrator:** paste the review notes (ASC_SUBMISSION_PACKET_S76.md section 6) after the demo accounts exist.
6. **Owner: screenshots** for the 6.9-inch or 6.5-inch iPhone set, at minimum (packet section 7). Install build 2 from TestFlight to capture them; this requires a TestFlight internal group, which the owner creates.
7. **Add for Review, then Submit.** This is the owner's final click, or the orchestrator's on the owner's explicit go.

## Follow-ups (not blocking the submission)

- **Move LANDING_BASE_URL to getmyez.com.** `SmartCompareApp/src/services/api.ts` keeps LANDING_BASE_URL on the Railway landing host. Move it once getmyez.com serves the landing; this needs an OTA plus the legalScreenLang.u8 pin.
- **U8 minors** (final adversaries 4 and 5, recorded):
  - Tie the AR-P1 presence pin to section 9.
  - Add the UF14 AR construction to `ug12_ar.terms_retired`.
  - Optionally move the AR section 9 qualifier.
  - Make privacy s3.6 name the compiled de-identified data as well.
  - Paraphrase gaps Z1-Z4 of the claim scan.
- **Sign in with Apple:** token revocation on account deletion (U11 = A, after launch).
- **Price coverage:** second-product price coverage (canary 7c: Galaxy S24 at 1/2 prices).
- **Worktree cleanup:**
  - sc-s76-domain and sc-s76-u10 hold node_modules junctions. Unlink with `cmd /c rmdir` first, then `git worktree remove`.
  - sc-s76-landing is plain.
  - sc-s70-u4b holds the only real node_modules: keep it.
- **SYNACKSOFTWARE:** move the Apple membership after the D-U-N-S arrives.

## Standing rules learned in session 76

- **PR helper:** never run `pr_rest.py watch` on a PR that must not auto-merge, because it merges when every check is green. Use `status`. `harness/pr_body.py get|set` edits a PR description.
- **Classifier limits:** the auto-mode classifier refuses DNS, domain and certificate changes even in bypassPermissions mode, and it treats retries as bypass attempts. Hand these steps to the owner with exact clicks.
- **Merges with main:** after merging main into a unit branch, run the FULL jest suite and the LF proof (a detached checkout with `core.autocrlf=false`) before pushing. Main's source scans and the Linux line endings caught three collisions that a dry merge could not show.
- **Orchestrator model:** the orchestrator switched to Opus 5.5 when the Fable weekly limit was hit (owner rule). Agents stay on Opus.

Ledger: `ledger.md` in this folder (the authoritative per-step record). Rulings: `specs/FABLE_RULINGS_U8_FIX4_S76.md` (UF14-UF26).
