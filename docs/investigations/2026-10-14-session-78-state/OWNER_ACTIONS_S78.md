# Owner actions, session 78 (2026-10-14)

Claude cannot do these: they are account, device, credential, attestation or legal steps. The order is by urgency.

## A. App Review response (do first)

1. **Accounts.** Create review accounts 1 and 2 in the app, then run the SQL in `DEMO_ACCOUNTS_SQL.md`. Send Claude the two emails, never the passwords.
2. **iPhone.**
   - Update the iPhone to the latest iOS.
   - Install 1.0.0 (2) from TestFlight. If TestFlight says "a developer has to invite you", redeem the invite email first.
3. **Dry run** (`RECORDING_SCRIPT.md` section A, steps 9-10). Report back three results:
   - Does "Continue with Google" sign you in?
   - Does the photo comparison work?
   - Does "iPhone 15 vs Samsung Galaxy S24" show a complete result?
4. **Record** with the shot list (section B), trim it, and move the file to the PC.
5. **Say "yes, fill App Store Connect".** Claude then ticks "Sign-in required" and pastes the new Notes. You type account 1's email and password into the Sign-In Information fields yourself.
6. **Say "yes, send".**
   - You attach the video, and the reply (`REPLY_DRAFT.txt`, signed "The MYEZ team") is sent.
   - Then press **Resubmit to App Review**. Claude re-warms the test pair just before, with your yes.

## B. Personal data and security (today)

7. **Make the GitHub repo private** (`KGRddhs/smartcompare-backend`). It publishes the home address, a personal mobile number, personal Gmail addresses and the whole architecture.
   - Check first: the Actions minutes on your plan (about 21 billed minutes per CI run), the Railway GitHub integration, and branch protection.
   - Rewriting history comes later and is optional. Existing clones and forks cannot be recalled.
8. **GitHub: turn on "Keep my email private"** (Settings > Emails) for future commits.
9. **Domain WHOIS.** Check the registrant records of getmyez.com and qaren.app for a visible name, address or phone, and turn on registrar privacy.
10. **Google Cloud OAuth consent screen.** Check the "User support email" and the developer contact. Every Google sign-in shows the support email. Use support@getmyez.com if it is personal.
11. **Supabase auth email sender.** Check the sender name and address of the auth emails.

## C. Legal (the redraft depends on these)

12. **A non-home address.** Get a Bahrain Post P.O. Box, or use a business-centre or registered-office address, in the controller's name, and give it to Claude. Bahrain PDPL Art. 17(1)(a) requires the controller's "full name ... and his address"; it does not require a home address.
13. **Your exact legal name.** Read the spelling on developer.apple.com > Membership: App Store Connect shows "Husain Aseeri", while the policy says "Hussain Aseeri". They must match.
14. **PDPA notification (Art. 14).** Confirm whether you filed the prior notification with the Personal Data Protection Authority, or appointed a Data Protection Guardian. Processing without it is an offence (Art. 58(1)(c)). The register is public (Art. 16(3)), so file with the P.O. Box, never the home address.
15. **Business mailbox.** Before release, move support@ and privacy@ off the personal Gmail forward to a business mailbox covered by a data processing agreement.
16. **Counsel (Bahrain).** Points to confirm:
    - whether a P.O. Box satisfies Art. 17;
    - the transfer basis for non-US processors;
    - the age of majority, for minors' contracts;
    - the carve-outs in the limitation of liability (Civil Code arts 58, 181, 219);
    - the indemnity.
17. **Second team member.** Add a written IP licence or assignment from the code author to the seller (Apple 5.2.1).

18. **EU Digital Services Act status (App Store Connect > App Information > App Store Regulations & Permits).** It is NOT set up (seen 2026-10-14 04:15). The app is rated for 172+ countries, so it is offered beyond the GCC, and without a DSA status Apple may remove it from sale in the EU. Pick one:
    - **Declare "not a trader"**, only if accurate for you: a free app with no income. This is a legal attestation, so it is yours to make.
    - **Limit Pricing and Availability to the GCC storefronts**, where the app's market and BHD prices are.

    Declaring "trader" would publish an address, phone and email on EU storefronts. Never use the home address or a personal mobile there.
19. **Version Copyright line.** It reads "2026 Hussain Aseeri". It must match your legal name spelling, or you can use the brand form you prefer.

Verified 2026-10-14: the License Agreement is "Apple's Standard License Agreement" (no custom EULA), which ToS v2 relies on. Keep it that way.

## D. Housekeeping (owed from session 77)

- Rotate the keys listed in `OWNER_ACTIONS_S77.md` item 12, one at a time with a smoke test. Confirm `ADMIN_API_KEY` was rotated after the value seen in git history.
- Delete the production smoke-test accounts created by `scripts/bundle_d_prod_smoke.py` and `tests/test_referral_e2e.py`.
- After the legal fix ships, check web.archive.org for old copies of the legal pages and request exclusion.
