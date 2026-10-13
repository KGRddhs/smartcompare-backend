# MYEZ legal, policy and exposure review: synthesis (main 10135306, 2026-10-11)

This is engineering due diligence, not legal advice. No lawyer has reviewed these texts yet (`counsel_review=false`). Anything marked UNVERIFIED was not confirmed against a primary source.

## 0. Corrections to the orchestrator's facts (re-checked today)
- **The getmyez.com apex is NOT behind the Cloudflare proxy any more.** It answers `Server: railway-hikari` with no cf-ray. The wildcard `*.getmyez.com` record is still proxied, and a random subdomain returns HTTP 525.
- **The Ahmed Jameel invite is already done.** S77 ledger 23:10: the owner invited ahmedjameel0703@gmail.com as **Admin**, not Developer. Ahmed accepted and was added to the TestFlight group "MYEZ Internal" with build 1.0.0 (2).
  - The invite is **not** a submission prerequisite. Its practical use is that it lets Ahmed's iPhone install build 2 for the smoke test and the screenshots.
  - Admin is broader than he needs. Reduce him to App Manager, limited to MYEZ, after submission. The name on his account shows a placeholder; fix it.
- **ADMIN_API_KEY was rotated on 2026-10-03** (CLAUDE.md:532). Two things are still owed:
  - The three old OpenAI keys still need revoking.
  - The production variables exposed in a local transcript on 2026-09-07 still need rotating (CLAUDE.md:36). They went into a local transcript, not the public repo.
- **Git history has no live credentials.** The scan covered OpenAI, AWS, GitHub, Supabase-secret, Stripe and Slack key shapes and .env files, and found none.
- **The repo is PUBLIC** (GitHub API: visibility public, 0 forks).

## 1. Verdict
MYEZ is close, but it should not press Submit until six cheap items are closed (section 2). Five of them are owner clicks or text edits, and one is a single OTA; none needs a new binary. Nothing in the published privacy policy or terms is blocked by App Review as written, and the live pages match the repo.

**The single biggest risk is OpenAI data sharing (decision D3 = C).** Every comparison, including photos and the inputs of 13-17-year-olds, goes into OpenAI's model-training programme in exchange for free tokens. Users can only refuse by not using the app. The policy meanwhile says "We do not sell your personal data" and the terms say "your personal data is never sold". Four exposures follow:
- Apple 5.1.2(i) says data may only be shared with third parties to improve the app or serve advertising. Training OpenAI's models is arguably neither.
- Apple 5.1.1(ii) requires an easy way to withdraw consent, and 5.1.1(iv) forbids forcing consent to unnecessary data access. Today consent can only be withdrawn by deleting the account.
- The same bundled consent is weak under the GCC data-protection laws.
- It is the most quotable headline against the app.

## 2. MUST FIX BEFORE SUBMISSION
| # | Issue | Why | Exact fix | Lever |
|---|---|---|---|---|
| M1 | OpenAI training-sharing (D3 = C) is bundled with the service, includes photos and minors, and is paid in free tokens, next to "we do not sell" (privacy s2, s4; ToS s8) | See the verdict above: Apple 5.1.2(i), 5.1.1(ii) and (iv), the PDPL freely-given-consent rule, and reputation | **Recommended, option A:** switch organisation data sharing OFF in the OpenAI dashboard. Apply the "Option A" wording in section 6 to privacy s2, s4 and ToS s8 (EN and AR). Remove the training sentence from the consent sheet `aiConsent.body` (EN and AR) and bump AI_CONSENT_VERSION to 3 in one OTA. **Option B:** keep sharing ON and publish the "Option B" wording, which states the token exchange. Under B the 5.1.2(i) and bundled-consent risks stay. | owner_decision + legal_text + code_client_ota |
| M2 | Credentials still owed rotation | A leaked Supabase service key exposes every user's account and comparison data, which would be a reportable breach. Old OpenAI keys allow spend billed to the owner. | Owner: revoke the three old OpenAI keys now. Rotate SUPABASE_SERVICE_KEY first, then the Upstash, Serper, Firecrawl and Scrape.do keys; renew Bright Data. Update web and price-warmer, redeploy, run one smoke compare. Record each rotation by name and date only. Delete the unused CLOUDFLARE_API_TOKEN. | infra_or_config |
| M3 | The repo is public | The public tree holds the internal rulings (the "free tokens" rationale, data-sale deliberations), the anti-bot scraping code, owner phone numbers and Gmail addresses, the infra account emails, and n=5 survey cells | GitHub → Settings → Danger zone → Change visibility to Private. Check the Actions-minutes quota first. Clones that already exist cannot be recalled, which is why M2 is the real fix. | owner_decision |
| M4 | The landing site makes claims a reviewer or brand can catch | 1. "sourced from authorized retailers" (landing/index.html:249, and the same word in the AR page).<br>2. "Coming soon to the App Store and Google Play", although no Android app is planned.<br>3. /bot says QarenBot "honours robots.txt", but the runtime price fetchers present themselves as Chrome, skip robots.txt and use Scrape.do "anti-bot bypass" (scrapedo_service.py:3). That contrast is public in the repo. | Use the section 6 landing wording (EN and AR), remove "Google Play", and redeploy the landing. Also check that the ASC description, promo text and keywords contain no "authorized" or "official" (UNVERIFIED). | legal_text (landing) |
| M5 | Mail to support@ and privacy@ is forwarded to a personal Gmail inbox; Google is not named as a recipient | Every data-subject request goes to an undisclosed recipient. The inbox is also not the controller's, so requests reach someone who is neither the controller nor under a processor agreement. | Change privacy s5 (EN and AR) to the section 6 wording, add Google (Gmail) to processors.json, then redeploy the backend /legal and re-render the landing. Better later: a mailbox on getmyez.com owned by the controller. | legal_text |
| M6 | Onboarding promises "Your name. Your email. Not now, not ever." (en.json:575, plus the AR twin and the defaultValue in Step05Trust) | The app's own share sheet can show your name, privacy s5 says invite recipients see your display name, and email goes to Supabase, Cloudflare and Gmail. The app contradicts its own policy, which is an Apple 2.3 and deceptive-claim problem. | One OTA (EN, AR and the Step05Trust defaultValue strings): change the head to "What we never do" and the body to "Sell your name or email, or send them to OpenAI." Ship it in the same OTA as M1, and keep the jest copy pins in sync. | code_client_ota |

Already in place, no action needed: the free tier with limits is stated in ToS s4, account deletion is complete (migration 043), store=False is set on every OpenAI call, no identity is sent to OpenAI, there are no ad or analytics SDKs, and the live legal pages equal the repo.

## 3. FIX SOON AFTER (before public release where marked *)
| Issue | Why | Fix | Lever |
|---|---|---|---|
| *DPAs not on file | Privacy s5 and s7 promise contractual protection, which Apple 5.1.1(i) requires. Do not soften the wording; back it. | Accept or download the DPAs from Supabase, OpenAI, Sentry, Railway, Upstash, Cloudflare and Expo. Check the terms of Serper, Firecrawl, Scrape.do and Bright Data. Keep copies privately. | owner_decision |
| *No written IP licence from Ahmed (code author) to Hussain (seller) | ToS s8 says the app belongs to "the publisher (or are licensed to us)". This is the biggest dispute risk between the two owners, and it blocks a clean move to SYNACKSOFTWARE and any data sale. | A short exclusive, worldwide, royalty-free licence or assignment, which can be assigned to the future company. Counsel drafts it. | owner_decision |
| *ToS s15/s16 conflict with Apple's standard EULA | s16 makes Apple's standard EULA apply, which brings California law and a US$50 cap (Apple standard EULA). s15 says Bahrain law and courts, and nothing says which prevails. | Add a precedence sentence (section 6). Counsel. | legal_text |
| *Supabase free plan has no backups and there is no breach runbook | Losing all data would be a data-protection integrity failure. s13 promises breach notification but no procedure exists. | Supabase Pro, plus a one-page runbook: contain, rotate, preserve logs, notify within the 72-hour target (deadlines per country for counsel). | infra_or_config |
| Consent is stored only on the device; no in-app way to withdraw (T04, T10) | The controller cannot prove consent. Apple 5.1.1(ii) asks for easy withdrawal. | Record ai_consent_version and ai_consent_at server-side (and add them to the 043 erasure list). Gate the compare, image and URL routes behind a flag. Add a "Withdraw AI permission" row in Profile → Privacy. | code_backend + OTA |
| Sign in with Apple tokens not revoked on deletion (U11) | Apple says apps "should" revoke (not "must"). Some reviewers raise it. | Call /auth/revoke when an account is deleted. If App Review raises it, reply in Resolution Center with the timeline. | code_backend |
| Account farming and denial-of-wallet | Throwaway emails can drain the OpenAI cap (US$120/month), and once it trips every compare fails for everyone. | A global daily compare ceiling, a disposable-email blocklist, and turning on ENABLE_SOCIAL_DEVICE_FINGERPRINT after its canary. **Do NOT turn on ENABLE_PROXY_AWARE_RATELIMIT** until rate_limiter.py:34-43 stops trusting the leftmost (attacker-controlled) X-Forwarded-For entry. | code_backend |
| Lockout denial of service | auth_service.py:44-45 locks an email for 15 minutes after 5 failures. Anyone who knows an email can keep that user locked out of password sign-in. | Key the lockout on IP plus email, or let a correct password or email link through. | code_backend |
| "No fixed period" retention; unsalted email hash (T11) | Storage-limitation principle; `sha256(email)[:16]` can be reversed by a dictionary attack. | Ship 044 with a cron (12 months for security logs, 24 months for anonymous logs). Switch to an HMAC with a server secret, then fill in the periods. | code_backend |
| Anon-readable SECURITY DEFINER views; anon grant on resolve_referral_code | A business-metrics leak and a Supabase advisor CRITICAL | `ALTER VIEW … SET (security_invoker=true)`, and revoke from anon and authenticated | code_backend |
| Wildcard DNS and missing DMARC | Brand subdomains point at an origin MYEZ does not control; support@ and privacy@ can be spoofed | Delete `*.getmyez.com`. Add `_dmarc` with `v=DMARC1; p=none; rua=…`, tighten to quarantine or reject only after checking the Supabase SMTP sender | infra_or_config |
| Health content | The results screen has a "Dosage" dimension, and drug_database_service feeds the prompt "ground truth for dosage" | Add the s6 health paragraph (section 6). Never break health categories down by demographics. | legal_text |
| Terms v2 pack | Hardening that makes the terms likely to be upheld (Civil Code art 58/59/181/219/223) | General section, liability carve-outs, AUP additions, trademark and takedown, change notice plus an archive of the 2026-10-11 version, minors wording, notices. Ship in **one** OTA window with the consent.ts TERMS_VERSION bump, because consent_service records the version the client sends. | legal_text + OTA |
| In-app absolutes still left | "never paid by sellers" (en.json:286, 750) becomes false at the first data sale. "25+ retailers" (en.json:279, 285, 544, 749) is unmeasured. "Real buys" comes from a 388-response survey, not purchases. | Measure the retailers per compare, then soften via OTA. Change the sellers line before any data deal. | code_client_ota |
| Robots.txt in code | The practice itself, not only the /bot text; Apple 5.2.2 | Check a cached robots.txt on runtime fetches, honour 429 and Retry-After, stop Chrome impersonation for hosts that block us, keep SCRAPEDO_SUPER off | code_backend |
| Small items | Accuracy and minimisation | - osBuildId in the fingerprint resets the free-tier lock on every iOS update; hash only the Keychain nonce. Fix the comment that says it "resets on uninstall".<br>- scripts/bundle_d_prod_smoke.py uses one fixed password for the prod accounts it creates; clean up those accounts and randomise it.<br>- Turn on Sentry "Prevent storing IP addresses" (UNVERIFIED current state).<br>- Align the Other Purposes rows between the ASC label (5 rows) and the manifest and packet (3 rows).<br>- Drop the unused Apple FULL_NAME scope.<br>- Confirm ENABLE_ZYTE_RENDER is off on web, or name Zyte in s5.<br>- Remove the unvalidated `cf-ipcountry` read. | mixed |

## 4. The owner's question: what data can MYEZ store and sell?
**What it may store today.** Everything on the published App Privacy label: 13 data types, linked to the user, no tracking. Each is defensible as long as four things hold:
- it is disclosed (it is);
- it is used only for the stated purposes;
- it is kept for a stated period (two "no fixed period" items still need one);
- it is protected (backups, rotated keys, private repo).

MYEZ already collects **less** than the big companies: no ad ID, no location, no contacts, no tracking SDK.

**What it may sell or license today.** Only **aggregated or anonymised statistics**, never personal data (privacy s2, ToS s8, ruling UG12). That is the same line OpenAI, Google, Microsoft and Amazon publicly draw:
- OpenAI says it does not sell personal data, shares de-identified data, and promises not to try to re-identify it.
- Google gives advertisers aggregated reports that do not reveal individuals.
- Amazon says it is "not in the business of selling" customers' personal information.

Even aggregated sales sit in a grey zone under Apple's literal text: 5.1.2(i) (share only to improve the app or serve ads), 5.1.2(ii) (no repurposing without consent) and DPLA 3.3.3(B). Get counsel before the first deal.

**What it may NOT do:**
- sell or share row-level, event-level or pseudonymous records, including "de-identified" free-text queries, photos, profile answers or any identifier;
- sell small demographic cells, for example governorate × age × gender in Bahrain (the repo's own survey has n=5 cells);
- break health or supplement searches down by demographics;
- sell to buyers who link the data to other data or use it for ad targeting;
- send anything per user. That counts as **tracking**: it needs the ATT prompt and "Tracking = Yes" on the label, and separate explicit consent under the GCC laws.

**How MYEZ compares with the big companies.** They store far more, and lawfully, because they carry the full apparatus: legal entities, data protection officers, signed DPAs, transfer mechanisms, fixed retention, per-purpose consent and opt-outs, and published no-re-identification promises. "Storing as much as big companies do" is not a legal test. The tests are purpose, legal basis, retention and security.

**To go further, with counsel:**
1. Add definitions and thresholds to the documents (section 6 block S6).
2. Export only through a query layer that enforces at least 50 accounts per cell, with suppression and an export log.
3. Sign a buyer contract that bans re-identification, linking with other data and onward sale.
4. Offer users an opt-out of statistics.
5. Write a legitimate-interest assessment and a DPIA.
6. File the Bahrain PDPA notification and do the Saudi SDAIA registration check.
7. For anything per user: separate opt-in consent, ATT, a label change and an updated policy.

## 5. Free with limits: exact wording
ToS s4 already says the app is free, with limits and no purchases, in both EN and AR. Two refinements are worth making:
- The current text implies 3 introductory comparisons plus 3 a day. In the code, the introductory comparisons count toward the daily and monthly counters (usage_service.py:314-361).
- Accounts can have different limits (review accounts raised by hand, referral bonuses).

Before finalising the first sentence, confirm the exact semantics of the lifetime-3 counter in usage_service.py.

**ToS s4 (replace):**
> MYEZ is free to use. To keep it free and to prevent abuse, each account has a comparison allowance: currently up to 3 comparisons a day and up to 10 a month (your first 3 comparisons count toward these), plus any referral rewards described in section 9. Unused comparisons do not carry over. We may change the allowance, set different allowances for some accounts (for example accounts we use for testing or promotions), and apply technical limits on how often requests can be sent. This version of the App sells no subscriptions, in-app purchases or paid features, and nothing in these Terms entitles you to a paid plan, to higher limits or to keep the current limits.

**App Store description (optional; it is locked after release; put it in the description only, not in the name, subtitle, keywords or screenshots):**
> MYEZ is free to use, with a daily and monthly comparison allowance.

## 6. Proposed English wording blocks (changed or added clauses only; each also needs its AR twin through the U8 machinery)
**S2, privacy s2 sentence 4**
- Option A (sharing OFF): "We do not sell your personal data, and we do not share it with data brokers or advertisers. OpenAI does not use your comparisons to train its models (section 4)."
- Option B (sharing ON): "We do not sell your personal data to data brokers or advertisers, and we do not share it with them. We take part in OpenAI's data-sharing programme (section 4): OpenAI may use the inputs we send it and the outputs it generates to evaluate and train its models, and in return OpenAI gives us some free use of its service."

**S4, privacy s4 programme paragraph**
- Option A: "We have switched off OpenAI's data-sharing programme for MYEZ: OpenAI does not use the inputs we send it or the outputs it generates to train its models. OpenAI may keep data sent to its API in abuse-monitoring logs for up to 30 days."
- Option B (keep the current paragraph and add): "In return for this sharing, OpenAI gives us complimentary use of its service. Please photograph products only, and do not include people, documents or personal or health details in photos or searches."

**ToS s8, last clause.** Replace "none of it identifies you, and your personal data is never sold" with:
- Option A: "none of it identifies you, and we do not sell your personal data."
- Option B: the same, plus "(section 4 of our Privacy Policy describes OpenAI's data-sharing programme)".

**Privacy s5, email line:** "Cloudflare and Google: Cloudflare receives the email you send to our addresses and forwards it to our mailbox provider, Google (Gmail), which stores it."

**Privacy s9, last sentence (replace):** "Aggregated statistics that cannot identify you may be kept after deletion." The code deletes the comparisons themselves (migration 043).

**Privacy s10, complaints (append):** "… or to the data protection authority of the country where you live."

**S6, privacy s2/s3.6 data-sale definitions (add before any data deal):** "'Aggregated' means statistics combined from at least 50 different accounts, with smaller groups left out. 'Anonymised' means data that neither we nor anyone who receives it can link back to you with means reasonably likely to be used. We never sell or license individual records, the text of your searches, your photos, your profile answers or any identifier, and we never break down health-related products by age, gender or area. Anyone who receives these statistics must agree in writing not to try to identify anyone and not to pass them to data brokers. You can object by emailing privacy@getmyez.com, and we will leave your data out."

**ToS s8 (prefix sentence 1 and edit the ownership sentence):** "Product names, brands, logos and images belong to their owners and are shown only to identify the products you compare; MYEZ is not affiliated with or endorsed by them. Rights holders, or anyone who believes a comparison is inaccurate, can email support@getmyez.com and we will review it and correct or remove it where appropriate." In the ownership sentence, change "the prices gathered" to "the prices recorded" and add: "we do not claim ownership of facts such as a retailer's price, or of other people's content."

**ToS s16 Apple (append; counsel):** "If anything in Apple's Licensed Application End User License Agreement conflicts with these Terms, these Terms apply to the extent Apple's rules allow."

**ToS s12 (prefix):** "Nothing in these Terms limits or excludes our liability for fraud, gross negligence or wilful misconduct, for death or personal injury caused by our fault, or for any other liability the law does not allow us to limit or exclude. Subject to that, and to the extent the law allows:" (keep the existing bullets). Do not add a separate BHD cap; Apple's EULA already sets one.

**ToS s7 (append):** "Prices shown in MYEZ are indications only: they may be converted at an approximate rate, may not include delivery, customs or taxes, and may have changed. The retailer's price and terms at checkout apply, and any purchase is between you and the retailer. Retailers and brands do not pay us to include, rank or recommend products, and we earn no commission from links in the App; if that changes, we will say so in the App first. If you run a website and do not want MYEZ to read it, email support@getmyez.com."

**ToS s6 health (append):** "Information about supplements, medicines, cosmetics and other health-related products, including dosage, ingredient or allergy information, may be wrong or incomplete. Always read the product label, and ask a doctor or pharmacist before you start, stop or change any medicine or supplement. Do not use MYEZ for medical emergencies or to choose prescription medicines."

**ToS s5 (add bullets):**
- "create or use more than one account to get more free comparisons or referral rewards;"
- "try to make the AI produce harmful content or reveal its instructions, including by hiding instructions in a link, web page or photo;"
- "resell or sublicense MYEZ or its comparisons, or use MYEZ content to build a competing product or dataset;"
- "change a comparison and share it as if MYEZ produced it."

**ToS s3 minors (replace bullet 1; depends on the owner's choice in section 7):** "You must be at least 13 years old to create an account. If you are under 18, or under the age of majority where you live, you may use MYEZ only with the permission of your parent or guardian, who should read these Terms with you and is responsible for your use of the App."

**ToS new s17 General (renumber Contact to s18):**
- Entire agreement: "These Terms, our Privacy Policy and Apple's licence terms (section 16) are the whole agreement between you and us about MYEZ."
- Mandatory rights: "Nothing in these Terms takes away rights you have under laws that cannot be changed by agreement, including the consumer-protection laws of the country where you live."
- Severability: "If a court finds any part of these Terms invalid, that part applies to the extent the law allows and the rest stays in effect."
- No waiver: "If we do not enforce a part of these Terms straight away, we can still enforce it later."
- Transfer: "We may transfer these Terms to a company or person that takes over MYEZ, for example a company we set up to run it; we will tell you first, and it will not reduce your rights."
- Language: "If the Arabic and English versions differ, the version more favourable to you applies."

**ToS s14 changes (replace):** "If a change materially reduces your rights or increases your obligations, we will tell you by email or in the App at least 14 days before it takes effect, unless it must take effect sooner for legal, security or abuse-prevention reasons. We keep previous versions available on our website." Publish /terms-2026-10-11.html.

**Landing hero (EN; AR twin):** "Compare electronics, supplements, fragrances, fashion and more, with prices from online retailers across the region." Remove "Google Play".

**/bot page:** "MYEZ looks up public product pages and store search results to find prices for the products our users compare. Our site-discovery crawler (QarenBot) reads and follows robots.txt. If you run a store and want us to stop or slow down, email support@getmyez.com and we will act within 5 working days."

## 7. Decisions only the owner can make
1. **D3: OpenAI data sharing.** Option A (OFF, recommended; it also removes most of the minors and photo risk) or option B (keep it and disclose the exchange). This must be decided before submission.
2. **Minimum age.** Keep 13+ with the guardian wording, raise it to 18+ (this changes the age rating and the checkbox), or keep 13+ and exclude under-18s from demographics and training.
3. **Repo private** (one click).
4. **Ahmed's ASC role.** Reduce Admin to App Manager, limited to MYEZ, after submission, and fix the placeholder name.
5. **The published home address** (Hamad Town) on three public pages and in the API. Replace it with a P.O. box or business address if counsel agrees it satisfies the contact duty.
6. **IP licence** Ahmed → Hussain, and when to move to SYNACKSOFTWARE.
7. **Supabase Pro** (backups) and a business mailbox for support@ and privacy@.
8. **When, if ever, to sell aggregated statistics, and to whom.** This decides the timing of the "never paid by sellers" copy change.
9. **Optional narrow user-indemnity clause.** Do not add a broad one.

## 8. Items for a Bahraini (GCC) lawyer
1. **Bahrain PDPL (Law 30/2018):**
   - Prior notification to the PDP Authority, or appointing a data protection guardian (Art 14 per secondary sources; UNVERIFIED).
   - Transfer basis for the US, India, Singapore and Germany against Resolution 42/2022's list (whether Singapore is listed is UNVERIFIED). "Required by contract" alone may not be a recognised basis.
   - A legal basis per purpose.
2. Whether the OpenAI token exchange is a "sale" or disclosure needing separate consent, and whether consent bundled with the service is valid (if D3 stays C).
3. **Minors:** Bahrain's age of majority (reportedly 21; UNVERIFIED), guardian consent, and Civil Code art 74 (minors' contracts can be annulled).
4. **Saudi PDPL:**
   - SDAIA overseas-controller registration (opened October 2026 per secondary sources).
   - A documented legitimate-interest assessment.
   - The transfer regulation.
   - Health inferences from supplement and pharmacy searches as sensitive data.
5. Whether the UAE (FDL 45/2021), Oman (RD 6/2022, consent for transfers), Qatar (Law 13/2016) and Kuwait (CITRA) laws apply to a foreign app, and the complaint routes in each.
6. **Breach-notification duties and deadlines per country.**
7. **Scraping:**
   - Exposure under computer-misuse law for the Scrape.do and Bright Data unblocking paths.
   - Retailer site terms.
   - Apple 5.2.2 and the ASC Content Rights answer.
   - Selling price-trend statistics built from scraped retailer pages.
8. **Before any data deal:** Apple DPLA 3.3.3(B) and guidelines 5.1.2(i) and (ii) against the UG12 statistics sale.
9. **Terms:**
   - Precedence over Apple's standard EULA (California law, US$50 cap).
   - Liability carve-outs under Civil Code art 181, 219 and 223.
   - Art 58 limits on unilateral changes and the notice period.
   - Language precedence (a native Arabic review is needed if Arabic is to prevail).
   - The GCC mandatory home-forum position.
10. **Controller and address:** that Hussain is correctly named as controller given Ahmed's operational role (a joint-controller or processor agreement may be needed), and whether a P.O. box satisfies the address duty.
11. Whether the 388 survey respondents consented to commercial reuse of their answers as cohort priors.
12. **Licence of the "bahrain_approved_drugs" registry data** used in prompts.

Sources cited by the reviewers: Apple App Review Guidelines (developer.apple.com/app-store/review/guidelines), Apple's account-deletion page, the App Store Connect add-users help page, the Apple standard EULA, the Apple DPLA, OpenAI help article 10306912 (search-indexed copy; the live page returned 403), the OpenAI, Google, Microsoft and Amazon privacy pages, the Bahrain Civil Code (WIPO BH083), and u.ae. The Bahrain and Saudi article numbers come from secondary sources (UNVERIFIED). Nothing was written in any repository.