## S77 LEGAL-DISCLOSURE

Owner decision M1 = Option B (keep OpenAI organisation data sharing ON and disclose it plainly), as amended by ruling RL10, plus M4 (landing claims) and M5 (the Gmail recipient). Spec `.qa-s77/LEGAL_DISCLOSURE_SPEC.md`; rulings RL1-RL13, LG1-LG9, RF1-RF3 (session-77 state folder).

### What changes
The live markdown and the pre-fill snapshot change in EN and AR through the U8 machinery. The four landing legal regions are re-rendered by `scripts/fill_in_legal.py` and `render_legal_landing.py`, never edited by hand.

**Not-sold promise and the OpenAI exchange**
- **Privacy s2 and terms s8.** The bare "not sold" sentences are replaced by one general promise: *"Apart from OpenAI's data-sharing programme described below, we do not sell or otherwise exchange your personal data for anything of value, and we do not share it with data brokers or advertisers."* It is followed by two disclosures: OpenAI may use inputs and outputs to evaluate and train its models, and OpenAI gives us some free use of its service in return. Aggregated or anonymised statistics stay permitted (UG12 / D4).
- **Privacy s4 (variant C).** Adds the exchange sentence and photo guidance.

**The Gmail recipient**
- **Privacy s5.**
  - The Google line also discloses that Google receives email sent to our addresses.
  - The Cloudflare line says that email is forwarded to our mailbox provider, Google (Gmail), under Google's own terms.
  - The own-terms sentence names Google as our mailbox provider (RL2).
  - `processors.json` gains the gmail row.
- **Privacy s7 (RL3).** The US recipients now read "United States (OpenAI and Google)".
- **Privacy s7 transfer sentence (RF1).** It now separates two groups: "service providers, which are required by contract to protect it", and "Google as our mailbox provider, which handles email under its own terms (section 5)". This removes the contradiction a legal adversary found.
- **Privacy s3.2 and s8 (RL11).** s3.2 now covers email sent to our addresses. s8 retention gains "kept in our mailbox until we delete it; no fixed period".
- **Privacy s9 (RF2).** Email sent to our addresses stays in our mailbox after account deletion. Users can ask privacy@getmyez.com to delete it.

**Accuracy and landing**
- **Terms s4 (RL6).** The limits parenthesis now matches the coded semantics in `usage_service.TIER_LIMITS`.
- **Landing (M4).**
  - The index pages drop "authorized retailers" and every Google Play claim and badge.
  - The `/bot` page claims robots.txt only for the QarenBot site-discovery crawler (RL8: no "honours", no 5-day promise).
  - README lines 30, 43 (LG7) and 52 are updated.

**Tests.** Pins were moved, never deleted (LG4, mutant-proven). New nodes D1-D18 are in `tests/test_legal_disclosure_s77.py`.

**Deviation outside the spec's file list.** In `SmartCompareApp/__tests__/landing.brand.s69.test.ts`, `ADDRESS_COUNTS` for `privacy.html` and `ar/privacy.html` changes from 10 to 11. The RF2 sentence adds one privacy@getmyez.com address, and D18 counts it with the jest pin's own regex. This CI's frontend job is the arbiter.

### Gates (local)
| Gate | Result |
|---|---|
| Unit files (disclosure + U8 + d3c + polish + routes) | 180 passed |
| Comm set | 885 passed |
| Extra set | 96 passed |
| `fill_in_legal.py` round-trip | Byte-identical |
| `render_legal_landing.py --check` | rc 0 |
| Pre-commit hook | Passed |
| Jest | Not run locally (no node_modules in the worktree) |

Adversaries:
- A legal adversary found 1 MAJOR, fixed by RF1-RF3.
- The final delta adversary found 0 blocking and 0 major.

### Owner decisions recorded or still owed
- **RL1 date note.** The effective date "October 11, 2026" and all twelve anchors are kept, and the API `last_updated` stays 2026-10-11.
  - This deliberately deviates from the literal promise in privacy s15 / terms s14 that a change updates the effective date.
  - Why: MYEZ 1.0.0 (2) is in App Review (submitted 2026-10-12, manual release, not released). Only the internal TestFlight testers and Apple's reviewer have seen any version, and the binary embeds TERMS_VERSION 2026-10-11 with no production-channel OTA.
  - The 2026-10-11 text is archived at git `10135306`.
  - The first post-release change must bump every anchor (including `consent.ts` TERMS_VERSION and `consent_service.TERMS_VERSION`) and publish the prior version.
- **RL7 / Q2.** Extending the terms s8 licence to OpenAI's own training use is out of this unit and needs an owner yes.
- **RL9 / Q5.** The free-use exchange goes into the consent sheet (`AI_CONSENT_VERSION` 3, sha fence re-pin) in the post-approval OTA.
- **App Store Connect.** The owner confirms the description, promotional text and keywords carry no "authorized", "official" or "Google Play".

### Deploy
1. Merge. Railway `web` auto-deploys, and the legal routes read the markdown per request.
2. Verify that /api/v1/legal/privacy_policy (EN and `?lang=ar`) contains "free use of its service" and "Google (Gmail)".
3. Redeploy the landing (the third lever) from a clean checkout of the merge SHA: `railway up landing --path-as-root -s qaren-landing -d`.

No OTA, no store build and no flag are involved.

### Stated limits
- **L1.** The consent sheet states the training use but not the free-use exchange until `AI_CONSENT_VERSION` 3 ships.
- **L2.** Apple 5.1.2(i) / 5.1.1 and GCC freely-given-consent risks remain: consent is bundled, and withdrawal is only possible by deleting the account. This unit makes the disclosure candid; it does not remove those risks.
- **L3.** The terms s8 licence still covers "obtaining comparisons from our AI provider", not OpenAI's own training use (owner Q2).
- **L4. The mailbox is the operator's personal Gmail.**
  - support@ and privacy@ forward to a personal Gmail account of the operator, not a controller-owned mailbox, and no DPA covers it.
  - s7 now separates contract-bound service providers from "Google as our mailbox provider, which handles email under its own terms (section 5)".
  - s9 says email to our addresses survives account deletion, with deletion on request at privacy@.
- **L5.** The `/bot` page does not say that price look-ups ignore robots.txt; it no longer claims they follow it. The robots.txt UA string still carries a personal Gmail contact.
- **L6.** Keeping the effective date conflicts with the literal s15/s14 promise (see RL1).
- **L7.** Under d3 = A, the plain-text s2, s3.6 and terms s8 sentences would describe a programme that the A variant of s4 denies. The recorded answer is d3 = C.
- **L8.** The AR (k) scan passes the new clauses only because no clause names a user's own item next to the AR "in return" / "for anything of value" words.
- **L9. Native Arabic review advised.** The Arabic is model-drafted MSA. These sentences need a native review:
  - the s2 / s4 / terms s8 disclosure sentences;
  - the s5 Gmail lines;
  - the s7 transfer sentence;
  - the s9 email sentence;
  - the s8 retention line.
- **L10.** Jest was not run locally; CI's frontend job is the arbiter.
- **L11.** Agents did not read the ASC metadata or the live pages.
- **L12.** The not-sold promise is now general, with the single OpenAI programme exception. Aggregated or anonymised statistics stay permitted.
- **Out of scope here** (follow-ups from the earlier adversary):
  - the landing index lede "prices from online retailers across the region";
  - README:52 vs README:141, and the Android assetlinks placeholder;
  - the AR P5G conditional style.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
