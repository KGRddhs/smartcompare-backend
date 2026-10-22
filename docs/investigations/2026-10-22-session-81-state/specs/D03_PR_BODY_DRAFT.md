# D03 DENY-AND-GUARDS: one per-call DENY_HOSTS module + unbiased counterfeit and luxury guards (`ENABLE_DATA_GUARDS_V2`, default OFF)

Unit D03 of PLAN_S81 (M1, lane B; Fable ruling F1). Branch `feature/s81-d03-deny-and-guards`, base `95cf6f864b4e70980ca191daa064c0118e223c13` (origin/main = #365). Spec `.qa-s80/D03_UNIT_SPEC.md` (sha `3460ffab...`), adversarial review APPROVE_WITH_CHANGES (B1-B5, RC1-RC12, corrections 1-18), rulings `specs/RULINGS_D03.md` (R-D03-1..4, B1-B5, C1-C12), RED gate `specs/GATE_D03.md` (GC-1..GC-7), all in `docs/investigations/2026-10-22-session-81-state/`. The URL-mode half is carved out to **D03b** (R-D03-1); prompt-input filtering is **D03c** (R-D03-2); the omega / tiffany tokens are **D03d** (R-D03-3).

## What the flag does

`ENABLE_DATA_GUARDS_V2` is a NEW name (unset in production by construction), read PER CALL with the house idiom (`os.getenv("ENABLE_DATA_GUARDS_V2", "false").strip().lower() in ("true","1","yes","on")`), one reader `app/services/deny_hosts.py::data_guards_v2_enabled`, the FIRST statement of every gated predicate.

New stdlib-only leaf `app/services/deny_hosts.py`: `DENY_HOSTS` (26 bare registrable domains: Fragrantica + 20 language editions, Parfumo .com/.de, Basenotes .com/.net, the Fragrantica image CDN fimgs.net), `DENY_LABELS`, `LEGACY_DESCRIPTOR_DENY_HOSTS`, `normalize_host`, `is_denied_host` (listed domain or subdomain, AND any host whose registrable label is fragrantica / parfumo / basenotes / fimgs with any public suffix: ruling C10 / GC-1; the suffix arm kept as defence in depth: GC-2), `is_denied_url`, `is_denied_source` (URL, host, or a source NAME carrying a banned label as a whole token), and the flag-FREE KB-writer guard `kb_source_allowed` / `assert_kb_source_allowed` / `DeniedSourceError` (no caller yet). No scheme literal anywhere (T7b-safe), never raises.

Effect ON:
1. `source_router`: all twelve registry consumers read `_routable_registry()` (flag OFF: `SOURCE_REGISTRY` itself; ON: a new list minus the denied rows, memoised with a STRONG reference to the registry object: ruling B4), so every selector, `build_site_discovery_query`, `score_source`, `source_usage`, `registry_tier`, `match_registry_apex`, `is_render_only_domain`, `_registry_row_for_host` and the descriptor lookup answer as if the denied rows were absent. `SOURCE_REGISTRY` / `_LITERAL_ROWS` byte-identical (the `:347` fragrantica literal stays; the R-A1 PR after approval deletes it).
2. `price_service.validate_scrape_url` returns False for a denied URL: the ONE never-fetched chokepoint every escalation / BH-tier / official-tier / organic-harvest candidate passes (ruling B2; closes review RC1's `/bh-en/` downgrade).
3. `rating_service`: a denied source (name or link) is tier 3 in `get_rating_tier`, skipped before tiering and the consensus in `extract_rating_from_shopping`, dropped by `collect_retailer_ratings`; the rating sets are untouched.
4. `review_service` (ruling B1, post-LLM, no digest moves): `build_retailer_quotes_from_reviews` never quotes a denied host; `clean_review_citations` writes no `Per <denied domain>:` attribution.
5. `search_descriptor_service._deny` uses the full rule (the probe refuses every denied host before a fetch); `DENY_HOSTS` there is the same tuple object as `deny_hosts.LEGACY_DESCRIPTOR_DENY_HOSTS`.
6. `image_service._is_valid_image_url` rejects a denied-host image in every tier; the Tier 1.5 piggyback override in `structured_comparison_service._fetch_product_data` goes through that validator under the flag (ruling C4).
7. `price_service.is_counterfeit_listing`: whole-token match + optional plural with LETTERS-only boundaries (C1), `copycat` kept via `_CF_V2_EXTRA_TOKENS` (C2), `replica` neutralised by a whole-token `margiela` (`COUNTERFEIT_BRAND_LINE_ALLOWLIST`; gold frag-018 prices).
8. `price_service.is_luxury_brand`: `lv` only as a whole token (`_LV_TOKEN_RE`); the 5 gold `lv` false positives (hair-005/010/012, supp-021, fash-015) clear. Blast radius named per C8: `strict_title_match`, `is_price_showable` via the designer floor, `effective_pair_size_ml` / `target_pair_size_ml` / `reselect_to_target_size`, the shopping sort and flagship bonus.

Flag OFF: byte-identical on every consumer (the P rows run with the FULL configuration: `ENABLE_URL_MODE_V2=true`, `ENABLE_LONGEST_HOST_MATCH` both states, a synthetic registry carrying one denied row of every selector shape, every falsy spelling).

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

250 nodes: 143 RED (fail at base on AssertionError only) + 107 PIN/GUARD (green at base). Flag: `ENABLE_DATA_GUARDS_V2`. Precondition: none to merge.

## Deliberate pin changes (spec 4.1)

None in the CI state (flag OFF): no existing test file is edited. ON-only reds (measured over the whole 409-file comm set with the flag exported for each runner call only; CI runs flag OFF; the later R-A1 PR re-pins them):

| Node | Why it goes red ON |
|---|---|
| `tests/test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2` | asserts the OFF rule (Fragrantica tier 2); ON a denied source is tier 3 (OQ-8) |
| `tests/test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped` | expects a quote from a cited Fragrantica result; ON it is skipped (ruling B1) |
| `tests/test_fragrance_content_quality.py::test_review_praise_no_interior_per_domain_artifact` | its precondition expects `Per fragrantica.com:` to be injected by `clean_review_citations`; ON the attribution is blank (ruling B1) |

The review also predicted `tests/test_review_paraphrase.py:42-50` and `:259` red ON; measured green ON (their inputs carry the `Per fragrantica.com:` text literally, not through `clean_review_citations`). `tests/test_retailer_quotes_from_reviews.py:74` stays green ON (an `issubset` assertion).

## Gates (GREEN head `5244f716`)

- ruff `--select E9,F63,F7,F82` on the 9 Python files: `All checks passed!` (ruff 0.16.5); `py_compile` clean; new files LF + pure ASCII; edited backend files CRLF with 0 bare LF and unchanged hi-byte counts; CLAUDE.md CRLF kept (+3 lines, 0 added hi-bytes).
- Unit file: `[pyt] tag=d03g-unit-on start=2026-10-22 18:23:08 end=2026-10-22 18:23:25 elapsed=17s bound=600s status=OK rc=0` (250 passed) and `[pyt] tag=d03g-unit-off start=2026-10-22 18:23:36 end=2026-10-22 18:23:51 elapsed=15s bound=600s status=OK rc=0` (250 passed); netguard 0, hermeticity 250.
- Pin group 1 (25 files: spec 1.10 groups + B1/B2 files): OFF `[pyt] tag=d03g-pins1-off ... elapsed=42s bound=600s status=OK rc=0` (639 passed); ON `[pyt] tag=d03g-pins1-on ... elapsed=43s bound=600s status=FAIL rc=1` (3 failed = the three ON-only reds above, 636 passed).
- Pin group 2 (22 files: url files, metering, model_config_enforced, prompt_fence, FY25, the W4-13 flag-OFF ledger, retro_w2_1, the 11 B5 adapter files): OFF `[pyt] tag=d03g-pins2-off ... elapsed=57s bound=600s status=OK rc=0` (471 passed, 1 skipped); ON `[pyt] tag=d03g-pins2-on ... elapsed=57s bound=600s status=OK rc=0` (same).
- CI-order set (48 files, sorted): `[pyt] tag=d03g-ci-order start=2026-10-22 19:19:49 end=2026-10-22 19:20:37 elapsed=48s bound=1200s status=OK rc=0` (1360 passed, 1 skipped).
- CLAUDE.md readers (34 files) on the final CLAUDE.md bytes: `[pyt] tag=d03g-claude-readers start=2026-10-22 19:20:54 end=2026-10-22 19:22:44 elapsed=110s bound=1200s status=OK rc=0` (1289 passed).
- Comm set (zero-regression gate): 409 files = the RED agent's 407 (module + symbol grep, path, walkers, named source-scanning pins, CLAUDE.md readers, SmartCompareApp scanners, B5) UNION 2 re-derived (`test_scoring_service.py`, `test_skill_frontmatter.py`), minus the 3 precommit hook files; 17 chunks of <= 25, bound 1200, flag OFF. HEAD: 18411 passed / 2 failed / 47 skipped / 37 deselected / 37 xfailed. Base (RED report): 18134 passed / 145 failed (143 unit RED + the same 2). HEAD failures = `tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest`, `tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction` (both in `tests/.pre_impl_failures.txt`). **branch-only-NEW = EMPTY.** netguard node set base 154 == head 154. Per-chunk `[pyt]` lines: `d03g-comm-head-01..17`, all `status=OK rc=0` except chunk 09 `status=FAIL rc=1` (the 2 baseline nodes).
- ON measurement (not a gate): the same 17 chunks with the flag exported: 18408 passed / 5 failed = the 2 baseline nodes + exactly the three ON-only reds; netguard set unchanged.
- GREEN mutation spot-check on the GREEN bytes (the full table is the adversaries'; the RED gate ran 52 on the prototype, 51 killed, M4 equivalent by GC-2): 16/16 KILLED by AssertionError (routable registry ungated; id-key memo without a strong reference; memo ignoring the registry; allowlist neutraliser on every keyword; alnum boundary; copycat dropped; validate_scrape_url ungated; attribution ungated; quotes unfiltered; piggyback bypassing / always using the validator; rating link unchecked; descriptor ignoring the flag; `lv` substring kept ON; label rule removed; port kept); restore sha-identical; `.qa-mutation.lock` removed.
- `scripts/verify_flag_byte_identity.py` is blind to this unit (its extraction path reaches none of the edited bodies; review correction 16).

## Stated limits

1. URL mode is D03b: until it lands a pasted denied link is still fetched (base and V2), a redirect hop onto one is followed, `normalize_image_url` can take a fimgs.net image; `url_routes.py` / `url_extraction_service.py` untouched (P14).
2. Denied-host organic text still reaches the specs / reviews / Tier-3 image prompts (D03c); only the Tier-3 output is refused.
3. `omega` / `tiffany` substring false positives untouched (D03d); "REPLICA Jazz Club" without the brand word and Amouage "Homage" still drop; a fake naming Margiela and `replica` and no other keyword passes.
4. The registrable-label rule is a stdlib heuristic: exotic multi-label public suffixes are not recognised (GC-3); the 26-host tuple still catches the listed hosts by suffix.
5. `registry_tier(<denied>)` is None ON; the global-tier genuine-label refusals no longer see it (the chokepoint keeps it unfetched; per the review, with `ENABLE_SHOPPING_CURRENCY_TRUTH` ON a Fragrantica Shopping row's relabel reason reads `no_bh_evidence`).
6. Direct `SOURCE_REGISTRY` readers outside `source_router` are untouched; the scs BH-locale memo still lists fragrantica.com, so a `/bh-en/` Fragrantica organic link reaches the off-registry rung and is refused only by the chokepoint (pinned both states, G11b). The filtered-registry memo does not see an in-place mutation of the same registry object (nothing mutates it).
7. The V2 counterfeit regexes are compiled at import from the keyword literals.
8. ON, the piggyback validator strips before the scheme test, so a whitespace-padded page image is taken where OFF it is not.
9. A rollback is per call for new computations only: ON-computed values stay in L1 for their TTL (price 24 h, genuine 7 d, Tier-3 estimate 12 h); a 30-day `nogenuine:` sentinel planted under OFF still suppresses Tier 1.5 on previously compared keys after the flip (C9).
10. Never set the flag in a local `.env`: the three ON-only reds above encode the OFF rule.

## Owner steps (names only)

None before merge. After approval, with the owner's explicit yes, set `ENABLE_DATA_GUARDS_V2=true` on `web` AND `price-warmer` in the SAME canary window (R-D03-4 / OQ-7). Canary on never-seen pairs or `nocache=true`: no `site:fragrantica.com` in the global discovery query log; zero `rating_source` / `retailer_quotes` / `Per fragrantica.com:` naming Fragrantica / Parfumo / Basenotes in fresh fragrance compares; zero `fimgs.net` in `products[i].image_url`; the counterfeit-rejection rate per category before vs after; the shopping-price coverage and per-pair size basis on Calvin Klein / Elvive / Centrum Silver pairs. Rollback: unset the variable on both services.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
