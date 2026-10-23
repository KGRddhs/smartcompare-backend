# OWNER_ACTIONS_S81 (names only, never values; written by the orchestrator 2026-10-22 ~22:10 AST; dependency order; tick items here or in chat)

Nothing below blocks the dark units now in flight (B4, D03, S81-03, ST1). FLIP-GATE items must be done before the named flag flips; RULING items are decisions the orchestrator asks for before the relevant flip and otherwise takes the bracketed default.

## A. Anthropic (before S81-06 ANTHROPIC-ROUTER can be canaried; S81-07 needs the test key)
1. Console: a dedicated MYEZ workspace; web search DISABLED at the organisation level until the registry allow-list exists (S81-21); the workspace spend limit at the current credit balance; confirm the usage tier and the credit expiry date (names and dates only).
2. Railway web: create ANTHROPIC_API_KEY (name only here). The worker service gets its own copy later (S81-19).
3. A separate TEST key for the S81-07 measurement spike (budget <= 15 USD, synthetic inputs only). RULING: confirm the spike budget [default 15 USD] and the seed budget [default 10 USD].
4. Does ANTHROPIC_API_KEY already exist on web? Answer by name as a ledger line.

## B. Names-only reads (R-A15; each lands as a dated ledger line)
5. Production flag STATES for: ENABLE_COMPARISON_ID_ECHO, ENABLE_SOCIAL_DEVICE_FINGERPRINT, ENABLE_LONGEST_HOST_MATCH, ENABLE_SYNC_DB_OFFLOAD, ENABLE_SITEMAP_INDEX, SERPER_IMAGE_DAILY_BUDGET (set or unset), OPENAI_MODEL_VISION (set or unset), STREAM_HARD_CAP_SECONDS (set or unset), ENABLE_SHOPPING_CURRENCY_TRUTH, ENABLE_BH_GCC_CATALOG_SOURCES, ENABLE_PROXY_AWARE_RATELIMIT, SCRAPEDO_SUPER (set or unset).
6. Read-only SQL (S81-02 / M3; results as counts): 14-day search_logs daily volume, fragrance share, repeat-pair share within 7 days, Serper calls per compare (is_synthetic excluded); pg_policies on the three 012 tables; the column lists of user_events and comparisons; whether comparison_feedback.useful is NOT NULL.
7. Supabase: the key TYPE the backend uses (anon vs secret), the Auth rate-limit values, SMTP state (built-in vs custom).

## C. Supabase changes (owner-only)
8. Raise the Auth dashboard sign-up and token limits now (S81-24 phase 1 lowers exposure later); custom SMTP; the SMTP provider then needs a processors.json row (the legal unit lists it).
9. Apply migrations when their units merge, PRECHECK first, POSTCHECK after: 045 KB core (S81-14), 046 feedback columns (SF1), 047 the 012 REVOKE (own file), 048 compare_runs (S81-22), 049 share_target and events widening (SF1), 050 if S81-03 chooses a spend-ledger table.

## D. Rulings the orchestrator will ask for (defaults in brackets)
10. Pre-v3 clients after the Claude flip: a short OpenAI transition window or immediate CONSENT_UPDATE_REQUIRED [default: 7 days of ENABLE_OPENAI_PRE_V3 after the OTA, then force-update via APP_MIN_VERSION].
11. Referral rewards vs the one 3/day/device rule [default: Loop-2 bonus comparisons and Deep Review credits suspended and their copy removed until re-designed]. FLIP-GATE for ENABLE_DEVICE_DAILY_QUOTA.
12. Live adapter user agent after the M6 named-UA capture dry-run [default: QarenBot if capture holds within 10 points].
13. Breaker caps per Riyadh day [live 3 USD / escalation 1 USD / search 0.50 USD / off-clock 2 USD].
14. Camera flip timing: with the build-3 permission-string mismatch accepted, or only after 1.0.1 is live.
15. Common Crawl CDX use for PDP discovery (D11 sub-flag) after reading the CC Terms.

## E. Legal track (no engineering before written terms)
16. FragranceX CJ Affiliate application; a Fragrances of the World licence request.
17. Counsel questions: retailer image hotlinking with provenance vs re-hosting (Bahrain/GCC); stale-price display; store-CTA independence and the Sponsored disclosure; operator-capture ToS per blocked host; the Anthropic cross-border transfer basis (PDPL art. 12-13); the minors policy statement; CC Terms.
18. LEGAL-V3 (S81-12) merges only in the flip window together with the backend deploy, the landing redeploy and the first OTA; the App Privacy label is updated BEFORE that OTA.

## F. Devices and builds
19. The #118 cert-pinning check over expo/fetch on a device (gates the SSE flip SS1/CL5).
20. Build-3 TestFlight: 5 cold starts and 5 compares per input type, timed (MS1 SPEED-BASELINE); WhatsApp canOpenURL and embedded Geist rendering; the Arabic walkthrough.
21. 1.0.1 native build after approval: provider-neutral camera/photo strings, react-native-share, expo-image, Cairo embedded, Sentry 8.x; Notes for Review (category narrowing, share targets, chips); replace the electronics screenshots.

## G. Landing, domain, partners
22. getmyez.com DNS to the landing service. (The public crawler page already exists: landing/bot/index.html, EN + AR, pinned by the S77 D9 test; the S81-15 cron needs the Railway cron service of item 25, not a new page.)
23. Play app-signing SHA-256 into assetlinks.json; APP_STORE_URL after approval.
24. Meta app id (Instagram Stories) and Snap Kit app + review for 1.0.1; the store-CTA contract template with the review-data clause; Trustpilot Data Solutions quote.

## H. After approval: the flip order (one canary window each, your explicit yes, fresh never-compared pairs in the ledger first)
LEGAL-V3 merged + backend + landing deployed -> first OTA (S81-08 headers + S81-11 honest UI + consent v3 copy) -> ledger, breaker, request context ON -> ENABLE_SYNC_DB_OFFLOAD + ST1 -> B1 result-status telemetry -> device quota + Riyadh reset + fragrance gate (after the v3 Terms are live and the header has propagated) -> text roles on Claude -> moderation on Claude after parity -> KB ingest -> KB-first serve -> live robots -> result gate -> compare-runs + judge -> camera on Claude -> OpenAI keys retired from web. Rollback for every flag = unset the variable.

## I. Added 2026-10-23 from the S81-15 and S81-12 rulings
25. Create a NEW Railway cron service for the robots registry cron (never web, never price-warmer): start command `python -m scripts.cron_robots_registry`, restart policy NEVER, the config file `railway.robots.json` the unit adds, variables by NAME only (SUPABASE_URL, SUPABASE_SERVICE_KEY, ENABLE_ROBOTS_REGISTRY_CRON, ROBOTS_CRON_MAX_HOSTS); schedule it daily only after migration 045 is applied and the seed's counts are in the ledger (R-S15-14).
26. On the LEGAL-V3 merge date (the first text-role flip window): turn OpenAI organisation data sharing OFF in the OpenAI console. It is a MERGE PRECONDITION for S81-12 and it ends the free-token allowance (remaining OpenAI traffic bills at list price) (R-S12-1).
27. Before the LEGAL-V3 window: confirm Anthropic's current commercial terms for API data retention (the 30-day default; any zero-data-retention option), training on API inputs (none by default), the usage-policy exception and the minors policy, or grant an agent a documentation read; the window commit records them with 'up to' periods (R-S12-13).
28. Your explicit yes for the S81-12 merge window itself: the held PR merges in the same window as the first ENABLE_ANTHROPIC_TEXT flip, with the landing redeployed and the backend deployed BEFORE the OTA; the counsel answers (item 17) are re-filled in that commit if they arrive before it (R-S12-15).
