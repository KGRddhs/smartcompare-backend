# D03 DENY-AND-GUARDS: one per-call DENY_HOSTS module + unbiased counterfeit and luxury guards (`ENABLE_DATA_GUARDS_V2`, default OFF)

Unit D03 of PLAN_S81 (M1, lane B; Fable ruling F1). Branch `feature/s81-d03-deny-and-guards`, base `95cf6f864b4e70980ca191daa064c0118e223c13` (origin/main = #365). Spec `.qa-s80/D03_UNIT_SPEC.md` (sha `3460ffab...`), adversarial review APPROVE_WITH_CHANGES (B1-B5, RC1-RC12, corrections 1-18), rulings `specs/RULINGS_D03.md` (R-D03-1..4, B1-B5, C1-C12), RED gate `specs/GATE_D03.md` (GC-1..GC-7), fix-round rulings `specs/RULINGS_FIX1_D03.md` (F1-1..F1-8), all in `docs/investigations/2026-10-22-session-81-state/`. The URL-mode half is carved out to **D03b** (R-D03-1); prompt-input filtering is **D03c** (R-D03-2); the omega / tiffany tokens (and a home for Ferragamo, MIN-4) are **D03d** (R-D03-3). Commits: the GREEN `5244f716` and fix round 1 (this PR's head).

## What the flag does

`ENABLE_DATA_GUARDS_V2` is a NEW name (unset in production by construction), read PER CALL with the house idiom (`os.getenv("ENABLE_DATA_GUARDS_V2", "false").strip().lower() in ("true","1","yes","on")`), one reader `app/services/deny_hosts.py::data_guards_v2_enabled`. The flag read precedes every behavioural branch; a pure base precondition (an empty-input check, the base image verdict) may run first (MIN-6). The order of the pure deny check and the flag read inside one condition (mutant XD6) is equivalent by ruling (MIN-E5).

New stdlib-only leaf `app/services/deny_hosts.py`: `DENY_HOSTS` (26 bare registrable domains: Fragrantica + 20 language editions, Parfumo .com/.de, Basenotes .com/.net, the Fragrantica image CDN fimgs.net), `DENY_LABELS`, `LEGACY_DESCRIPTOR_DENY_HOSTS`, `normalize_host`, `is_denied_host` (listed domain or subdomain, AND any host whose registrable label is fragrantica / parfumo / basenotes / fimgs with any public suffix: ruling C10 / GC-1; the suffix arm kept as defence in depth: GC-2), `is_denied_url` (the parsed HOSTNAME, userinfo and port removed, never the netloc; an authority carrying a backslash is denied when a banned label appears anywhere in it, because a WHATWG parser reads such an authority differently: F1-4), `is_denied_source` (URL, host, or a source NAME carrying a banned label as a whole token), and the flag-FREE KB-writer guard `kb_source_allowed` / `assert_kb_source_allowed` / `DeniedSourceError` (no caller yet). The module holds the two deny literal tuples, `DENY_HOSTS` and the re-exported `LEGACY_DESCRIPTOR_DENY_HOSTS`; no other deny literal list exists in `app/` (R1i scans every module but this one; MIN-E2). No scheme literal anywhere (T7b-safe), never raises.

Effect ON:
1. `source_router`: all twelve registry consumers read `_routable_registry()` (flag OFF: `SOURCE_REGISTRY` itself; ON: a new list minus the denied rows, memoised with a STRONG reference to the registry object: ruling B4), so every selector, `build_site_discovery_query`, `score_source`, `source_usage`, `registry_tier`, `match_registry_apex`, `is_render_only_domain`, `_registry_row_for_host` and the descriptor lookup answer as if the denied rows were absent. `SOURCE_REGISTRY` / `_LITERAL_ROWS` byte-identical (the fragrantica.com `Source` literal in `_LITERAL_ROWS` stays; the R-A1 PR after approval deletes it; MIN-E1).
2. `price_service.validate_scrape_url` returns False for a denied URL: the ONE never-fetched chokepoint every escalation / BH-tier / official-tier / organic-harvest candidate passes (ruling B2; closes review RC1's `/bh-en/` downgrade).
3. `rating_service`: a denied source (name or link) is tier 3 in `get_rating_tier`, skipped before tiering and the consensus in `extract_rating_from_shopping`, dropped by `collect_retailer_ratings` before its dedup (pinned, F1-3); the rating sets are untouched.
4. `review_service` (ruling B1, post-LLM, no digest moves): `build_retailer_quotes_from_reviews` never quotes a denied host; `clean_review_citations` writes no `Per <denied domain>:` attribution; both decide on the cited link's parsed hostname through `is_denied_url`, so a userinfo or backslash link is denied too (F1-4 / MIN-3).
5. `search_descriptor_service._deny` uses the full rule (the probe refuses every denied host before a fetch); `DENY_HOSTS` there is the same tuple object as `deny_hosts.LEGACY_DESCRIPTOR_DENY_HOSTS`.
6. `image_service._is_valid_image_url` rejects a denied-host image in every tier; the Tier 1.5 piggyback override in `structured_comparison_service._fetch_product_data` goes through that validator under the flag (ruling C4), reached as the module attribute `image_service._is_valid_image_url` so a patch of it takes effect (F1-6 / MIN-E9), and stores the stripped url (pinned, F1-5).
7. `price_service.is_counterfeit_listing`: whole-token match + optional plural with LETTERS-only boundaries (C1), `copycat` kept via `_CF_V2_EXTRA_TOKENS` (C2), `replica` neutralised by a whole-token `margiela` (`COUNTERFEIT_BRAND_LINE_ALLOWLIST`; gold frag-018 prices).
8. `price_service.is_luxury_brand`: `lv` only as a whole token (`_LV_TOKEN_RE`); the 5 gold `lv` false positives (hair-005/010/012, supp-021, fash-015) clear. Blast radius named per C8: `strict_title_match`, `is_price_showable` via the designer floor, `effective_pair_size_ml` / `target_pair_size_ml` / `reselect_to_target_size`, the shopping sort and flagship bonus.
9. The Serper-Shopping door (F1-1 = MAJ-1 / MAJ-E1; Shopping rows are priced from the payload and never fetched, so the chokepoint of item 2 does not cover them): `price_service.extract_price_from_shopping` and the scs re-selection stash `_seed_shortcircuit_candidates` drop a row whose link host or source name is denied (`_drop_denied_shopping_rows` over `_shopping_row_denied`; a new list, the shared `_shopping_items_cache` list untouched) BEFORE any currency, evidence or short-circuit logic: never a candidate, never a `local_bhd` / `converted_usd` label, never a stash seed, in both `ENABLE_SHOPPING_CURRENCY_TRUTH` states and for every ask (a pool of only denied rows yields no Shopping price); `_shopping_bh_host_evidence` returns the new reason `denied_host` before every rung; ONE INFO line per extraction call that dropped a row, `[DATA_GUARDS_V2] shopping rows dropped (denied host) count=<n> by=link|source host=<hostname>` (constants, an int and a hostname; the stash is silent because the front door logged the same pool; the W4-7 listing-count replay filters the line, and that count no longer counts such a row).

Flag OFF: byte-identical on every consumer (the P rows run with the FULL configuration: `ENABLE_URL_MODE_V2=true`, `ENABLE_LONGEST_HOST_MATCH` both states, a synthetic registry carrying one denied row of every selector shape, every falsy spelling; the F1 OFF pins add the adversary probe3 shape: under `ENABLE_SHOPPING_CURRENCY_TRUTH` ON a Fragrantica `/bh-en/` Shopping row is priced `converted_usd` with the base reason `global_tier`, under it OFF `local_bhd`; the cheapest denied row wins its pool, the stash seeds every row, no `[DATA_GUARDS_V2]` line; the userinfo link is quoted and attributed by its netloc exactly as at `5244f716`).

## Defect ids -> RED nodes -> flag

| Finding (source) | RED rows (`tests/test_s81_d03_deny_and_guards.py`) | PIN / GUARD rows |
|---|---|---|
| Banned sources live in the router, discovery and ratings (VERIFY C2.1 / C2.3, PLAN F1) | R1a-R1i (module, 26 hosts, label rule C10/GC-1, single literal list C11), R3a (40), R3b, R3c, R3d, R3e (B4), R4a-R4f (incl. C12 neutral source + denied link) | P1 (16), P1b, P2, P3 (8), P3b, P11 (8) |
| Descriptor deny list covers two hosts only | R2a (5), R2b (3) | P4 (8), P4b, G2a (3) |
| Denied images (fimgs.net) shown (VERIFY C6.6, review RC2 / C4) | R7a (4), R7b, R7c, R7d, R7e (scs piggyback runs for real) | P9 (8), P9b (3), P9c, G7a, G9c |
| Banned display surfaces: retailer quotes + `Per <domain>:` (review B1 / RC3) | R10a, R10b | P12 (8) |
| "As if absent" downgrades a fail-closed refusal (review B2 / RC1) | R11a | P13 (8), G11b (2, both states) |
| Counterfeit substring bias: frag-018, infused, unused, copyright (R15; C1, C2) | R5a (2), R5b (5), R5c (frag-018 prices 45.0), R5d, R5e | P5 (8), P6 counterfeit (11 incl. copycat, 1:1replica, Replica1), P6b, P7 (2), P8 |
| Luxury `lv` substring bias: Silver, Calvin, Elvive (R15) | R6a (8), R6b (2), R6c (Calvin Klein floor) | P5, P6 luxury (4), P7 |
| KB-writer guard for later units | R9a, R9b (8, flag-free) | - |
| D03b scope fence (R-D03-1, GC-4) | - | P14 |
| FIX1 F1-1 (MAJ-1 = MAJ-E1): the Serper-Shopping door bypasses the deny list | f1_1a (4: W4-1 off/on x BHD/AED; the next allowed row wins, a denied-only pool yields None), f1_1b (4: the evidence helper returns `denied_host`), f1_1c (no currency / evidence logic and no W4-1 line for a denied row; ONE host-only D03 line), f1_1d (4: the stash seeds no denied row), f1_1e (the stash never consults evidence for one) | f1_1p (8, the probe3 shape OFF) |
| FIX1 F1-2 (MIN-1, mutant A9): two-level public suffix | - | f1_2 (fragrantica.co.uk, parfumo.com.au, basenotes.co.nz, fimgs.net:8443 denied; fragrantica.co.uk.evil.test not) |
| FIX1 F1-3 (MIN-2, mutant D6): deny before dedup | - | f1_3 |
| FIX1 F1-4 (MIN-3 + MIN-E7): userinfo and the backslash authority | f1_4a (2: review quotes + attribution, userinfo and backslash links), f1_4b (backslash authority in `is_denied_url` and the image validator) | f1_4p (hostname rules: userinfo denied, a label in the query / path not), f1_4q (8, OFF base attribution) |
| FIX1 F1-5 (MIN-5, mutant G3): the piggyback strip | - | f1_5 |
| FIX1 F1-6 (MIN-E9): patchable validator import | f1_6 (fails at `5244f716` by construction: the by-name import is the defect it pins) | - |

288 nodes: 161 RED (143 fail at base `95cf6f86`, 18 fail at `5244f716`; every one on an AssertionError only) + 127 PIN/GUARD (107 + 20, green at their base). Flag: `ENABLE_DATA_GUARDS_V2`. Precondition: none to merge.

## Deliberate pin changes (spec 4.1)

None in the CI state (flag OFF): no existing test file is edited. ON-only reds (measured over the whole 409-file comm set at the GREEN head, and again at the fix-round head over both pin groups and the 38-file Shopping set, with the flag exported for each runner call only; CI runs flag OFF; the later R-A1 PR re-pins them):

| Node | Why it goes red ON |
|---|---|
| `tests/test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2` | asserts the OFF rule (Fragrantica tier 2); ON a denied source is tier 3 (OQ-8) |
| `tests/test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped` | asserts the quote of the cited Basenotes result (`quotes[0]["retailer"] == "basenotes.net"`, snippet 2); ON Basenotes is denied, so the quote is skipped (ruling B1; MIN-E3) |
| `tests/test_fragrance_content_quality.py::test_review_praise_no_interior_per_domain_artifact` | its precondition expects `Per fragrantica.com:` to be injected by `clean_review_citations`; ON the attribution is blank (ruling B1) |

The review also predicted `tests/test_review_paraphrase.py:42-50` and `:259` red ON; measured green ON (their inputs carry the `Per fragrantica.com:` text literally, not through `clean_review_citations`). `tests/test_retailer_quotes_from_reviews.py:74` stays green ON (an `issubset` assertion). The W4-1 / W4-2 Shopping pins stay green ON (none uses a denied host).

## Gates

GREEN head `5244f716` (unchanged lines of the GREEN draft):
- ruff `--select E9,F63,F7,F82` on the 9 Python files: `All checks passed!` (ruff 0.16.5); `py_compile` clean; unit `d03g-unit-on` / `d03g-unit-off` 250 passed; pin group 1 OFF 639 passed, ON 3 failed (the three above); pin group 2 OFF/ON 471 passed; CI-order set (48 files) 1360 passed; CLAUDE.md readers 1289 passed; comm set 409 files / 17 chunks: HEAD 18411 passed / 2 failed (the 2 `tests/.pre_impl_failures.txt` page_scraping nodes), branch-only-NEW EMPTY; GREEN 16-mutant spot-check 16/16 KILLED.

Fix round 1 (this head; every `[pyt]` line in the fix report `D03_FIX1_REPORT.md`):
- RED step at `5244f716` (the four app files at their `5244f716` bytes, the final RED rows): `[pyt] tag=d03f1-mut-HEADCODE ... status=FAIL rc=1`: exactly the 18 new RED nodes fail, every one an AssertionError; 270 passed (the 250 frozen rows + the 20 new PIN rows).
- Unit file on the final bytes: `[pyt] tag=d03f1-unit-off-final ... status=OK rc=0` (288 passed) and `[pyt] tag=d03f1-unit-on-final ... status=OK rc=0` (288 passed); netguard 0, hermeticity 288.
- Mutation table (byte copies, exact-once edits, the whole unit file, restore sha-identical): 22/22 KILLED by AssertionError: the three F1-1 site mutants (front door, evidence helper, stash), the check-after-evidence mutants at the front door and the stash, the three ungated variants, the link-only / source-only variants, the per-row log and the URL-in-log mutants, A9, D6, the two userinfo (netloc) mutants in `review_service`, the `is_denied_url` netloc mutant, the backslash rule removed / applied to the whole URL / applied without a backslash, G3, and the by-name validator import; the five `deny_hosts.py` mutants re-run on the post-black bytes.
- Pin group 1 OFF 639 passed; ON 3 failed = exactly the three ON-only reds above; pin group 2 OFF 471 passed, ON 471 passed.
- Shopping set re-derived (38 files: every test referencing `extract_price_from_shopping`, `_seed_shortcircuit_candidates`, `_shopping_bh_host_evidence`, the W4-1 / W4-2 flags, plus `tests/test_hotfix_shopping_query_clean.py`), two chunks, cheapest first: OFF 262 + 1321 passed, ON 262 + 1321 passed.
- CI-order set (81 files sorted: the GREEN 48 + the Shopping set + `tests/test_ci_gates.py`): 2555 passed, 1 skipped.
- Comm set (the GREEN 409 + `tests/test_hotfix_shopping_query_clean.py` = 410 files, 17 chunks, flag OFF): 18463 passed / 2 failed = the same 2 `tests/.pre_impl_failures.txt` page_scraping nodes; branch-only-NEW EMPTY.
- CLAUDE.md readers (34 files) on the final CLAUDE.md bytes: 1289 passed.
- ruff blocking tier + py_compile on the 5 edited Python files clean; the wider F401/F811/F841 pass 28 at `5244f716` and 28 here (0 new); `black 26.5.1 --check` clean on `app/services/deny_hosts.py` and the RED file, both added to `.github/black-clean-paths.txt` (F1-7; formatting only, AST-identical before/after black).
- Byte checks: the edited CRLF backend files keep CRLF with 0 bare LF and unchanged counts of bytes > 127; the two LF files stay LF with 0 bytes > 127; CLAUDE.md 943 CRLF lines, 3961 bytes > 127 before and after.
- `scripts/verify_flag_byte_identity.py` is blind to this unit (its extraction path reaches none of the edited bodies; review correction 16).

## Stated limits

1. URL mode is D03b: until it lands a pasted denied link is still fetched (base and V2), a redirect hop onto one is followed, `normalize_image_url` can take a fimgs.net image; `url_routes.py` / `url_extraction_service.py` untouched (P14).
2. Denied-host organic text still reaches the specs / reviews / Tier-3 image prompts (D03c); only the Tier-3 output is refused.
3. `omega` / `tiffany` substring false positives untouched (D03d); "REPLICA Jazz Club" without the brand word still drops, and so does any title carrying "homage", "inspired", "generic", "alternative" or "vintage" as a whole word (spec L8; Amouage Homage Attar is a genuine product, OQ-5); a fake naming Margiela and `replica` and no other keyword passes.
4. The registrable-label rule is a stdlib heuristic: exotic multi-label public suffixes are not recognised (GC-3); the 26-host tuple still catches the listed hosts by suffix.
5. `registry_tier(<denied>)` is None ON, so the global-tier genuine-label refusals no longer see it, and no path turns that into a fetch or a label: the chokepoint keeps a denied URL unfetched and the Shopping door (item 9) drops a denied Shopping row before the W4-1 evidence rule. Before fix round 1 both adversaries measured a Fragrantica `/bh-en/` Shopping row relabelled `converted_usd` -> `local_bhd` under `ENABLE_SHOPPING_CURRENCY_TRUTH` ON (MAJ-1 / MAJ-E1), and the row was priced in every state.
6. Direct `SOURCE_REGISTRY` readers outside `source_router` are untouched; the scs BH-locale memo still lists fragrantica.com, so a `/bh-en/` Fragrantica organic link reaches the off-registry rung and is refused only by the chokepoint (pinned both states, G11b). The filtered-registry memo does not see an in-place mutation of the same registry object (nothing mutates it; GREEN Q1, accepted).
7. The V2 counterfeit regexes are compiled at import from the keyword literals.
8. ON, the piggyback validator strips before the scheme test, so a whitespace-padded page image is taken (and stored stripped) where OFF it is not.
9. A rollback is per call for new computations only: ON-computed values stay in L1 for their TTL (price 24 h, genuine 7 d, Tier-3 estimate 12 h); a 30-day `nogenuine:` sentinel planted under OFF still suppresses Tier 1.5 on previously compared keys after the flip (C9).
10. Never set the flag in a local `.env`: the three ON-only reds above encode the OFF rule.
11. ON a fragrance compare's global discovery window holds 3 domains instead of 4 (`site:amazon.com OR site:sephora.com OR site:walmart.com`; no replacement row exists in either catalog state; spec L10); the Serper call count is unchanged.
12. `LVs Neverfull` is luxury at base and not ON (review correction 18).
13. Salvatore Ferragamo is in neither brand table and was luxury / designer at base only through the `lv` substring inside "salvatore": ON it loses `is_luxury_brand`, the designer low-price floor (an 8 BHD decant-class listing of a Ferragamo 100 ml is no longer floored) and the flagship pair basis; "Creed Silver Mountain Water" keeps the designer floor but loses `is_luxury_brand` (MIN-4; a home for Ferragamo is D03d; both are canary pairs).
14. The backslash rule is deliberately conservative: an authority carrying a backslash is denied when a banned label appears anywhere in it, even where a WHATWG parser would read another host; the list is a policy list, not a security boundary (`url_validator` uses the same parser).
15. "One INFO line per request" is implemented as one line per `extract_price_from_shopping` call, so a compare logs at most one line per Shopping pool it prices (a request-scoped latch needs a request context these files do not own).

## Follow-ups (recorded, not D03)

- MIN-7 (pre-existing): `clean_review_citations` copies `reviews` shallowly (`dict(reviews)`) and rewrites `review_summary` in place, so a second call on the same dict loses the citation markers.
- MIN-E8 (orchestrator): DEFECT_LEDGER rows for D03, D03b, D03c, D03d (written 2026-10-22).
- D03d: the omega / tiffany tokens and a home for Salvatore Ferragamo.

## Owner steps (names only)

None before merge. After approval, with the owner's explicit yes, set `ENABLE_DATA_GUARDS_V2=true` on `web` AND `price-warmer` in the SAME canary window (R-D03-4 / OQ-7). Canary on never-seen pairs or `nocache=true`: no `site:fragrantica.com` in the global discovery query log; zero `rating_source` / `retailer_quotes` / `Per fragrantica.com:` naming Fragrantica / Parfumo / Basenotes in fresh fragrance compares; zero `fimgs.net` in `products[i].image_url`; zero Shopping `price.retailer` / `price.url` on a denied host, and the count of `[DATA_GUARDS_V2] shopping rows dropped` lines; the counterfeit-rejection rate per category before vs after; the shopping-price coverage and per-pair size basis on Calvin Klein / Elvive / Centrum Silver / Salvatore Ferragamo / Creed Silver Mountain Water pairs. Rollback: unset the variable on both services.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
