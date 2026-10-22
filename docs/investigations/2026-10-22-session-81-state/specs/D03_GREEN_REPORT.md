# D03 GREEN REPORT (DENY-AND-GUARDS, ENABLE_DATA_GUARDS_V2)

- Agent: GREEN, model Opus 5.5 (claude-opus-5-5); the task text called it "Fable", the session pin is Opus 5.5.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-d03; branch feature/s81-d03-deny-and-guards; base 95cf6f864b4e70980ca191daa064c0118e223c13; HEAD 5244f7165dbde49579a9f4147229b20050427c18 (one commit on the base, not pushed, no rebase, no PR).
- RED file tests/test_s81_d03_deny_and_guards.py sha256 ae8fffc7ffe50205af9170a82f1de22ca38e629482b1afc93bf1c0181610449c: re-hashed at start, before commit, after commit (working copy and the committed blob): MATCH every time; not edited.
- git status --short after the commit: EMPTY.
- Notes, logs, scripts: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/D03_green/ (notes.md, pyt_lines.txt, comm_set.txt, comm_set_reasons.tsv, comm_head/, comm_headon/, mut/, mutation_results_*.json, PR_BODY.md). Byte copies of every edited file: .../scratchpad/D03_green_before/ (SHA256SUMS.json).

## Files (sha256 before -> after, numstat vs base)

| path | before | after | +/- |
|---|---|---|---|
| app/services/deny_hosts.py (NEW, LF, ASCII) | - | 750ea9ed19e42db385a54360dd979ad5eb3daf805cf71c5a5eea299399c354c8 | +226 |
| app/services/search_descriptor_service.py | b86e2770eb067326a7e4771de609dc52232faf9e74c46db794500d1ff3481723 | f627e4e980f9d9023a6a60466e34c56a1327fbe05cc53bd625cbadde90983996 | +10 -1 |
| app/services/source_router.py | e76edea1cfcefab0b9a71abd15f4191c329172b614ced88d2bd4c519e7f2dc34 | afd3dd24839242dde6f771ceb763ea3e3730d3ad2c75cc35482243b51c626713 | +39 -12 |
| app/services/rating_service.py | 89541b416911f761e9ca00ae9b53111f65a0829a436150312b5d317c5336a02d | 64abc44cc1ca7840f6bc10f1d96e4716ad8b0a213960a72652be967907236cdd | +26 |
| app/services/price_service.py | d38487fd907dad832eecc5ec422482992495c7bb4590eab0f45e72278caa6d2c | 2541648923bdd6dc3da7c0928bcd3ca679ef9d582af8de9477e566a42850cc95 | +69 |
| app/services/image_service.py | cbb4fa82850086969c522c2fcdd98ad1736bdb5de7cfe7284155c158a1b867dd | 31d67f167f13517bdfdcf8dae2b649f0a66e46b6f3747ebcefe2a80fde0707f4 | +8 -1 |
| app/services/review_service.py | ab6979ece0bac60c9997ddb55d052bd03a7255e1924fe54cf86219cb0aec3931 | 05d7c079ba83978fb48dbed43dcaba2992840a259f3b679fdd8b02aba54afbeb | +10 |
| app/services/structured_comparison_service.py | ff33fdd96f744645626266ef85e03e3fc5a53864b6002f7cee83e5ad3f74cad7 | ec5b8d2b0a1538fd90d785bae5a7201ad66c8e26acdbb0b5e31aaade8bc78b34 | +12 -1 |
| CLAUDE.md (CRLF kept) | cf89f79567a7157a5d46b4fbed0b98b1bb5ede5527d8ff8ec843bfef804d2093 | 4cc6941891c6d802bc38ed67a866f8f85dde760a65d2c47301cae3b31dd0a1ef | +3 |
| tests/test_s81_d03_deny_and_guards.py (RED, frozen) | ae8fffc7ffe50205af9170a82f1de22ca38e629482b1afc93bf1c0181610449c | ae8fffc7ffe50205af9170a82f1de22ca38e629482b1afc93bf1c0181610449c | +1316 (new to the index) |

Byte checks: the 7 edited CRLF backend files have 0 bare LF and unchanged counts of bytes > 127; deny_hosts.py LF, 0 bytes > 127, no "http" substring; CLAUDE.md 943 CRLF / 943 LF, 3961 bytes > 127 before and after (0 added). Personal-value / key-shape sweep over every added line: 0 hits.

## Implementation (cite by function)

- deny_hosts.py: DENY_HOSTS (26), DENY_LABELS, LEGACY_DESCRIPTOR_DENY_HOSTS, data_guards_v2_enabled (house idiom, per call), normalize_host (strip, lower, drop :port, trailing dots, one www.), _registrable_label (GC-3 heuristic), is_denied_host (suffix arm GC-2 + label rule C10), is_denied_url (schemeless and protocol-relative read as //host; ValueError -> False), is_denied_source (URL / host / whole-token label), DeniedSourceError, kb_source_allowed, assert_kb_source_allowed. Stdlib only.
- search_descriptor_service: module import of deny_hosts; DENY_HOSTS = deny_hosts.LEGACY_DESCRIPTOR_DENY_HOSTS (same object); _deny: flag first -> is_denied_host, else the base body.
- source_router: import from deny_hosts; _ROUTABLE_MEMO + _routable_registry() (OFF returns SOURCE_REGISTRY; ON a new filtered list; memo (registry, filtered) with a strong reference, hit only when memo[0] is SOURCE_REGISTRY: ruling B4); the twelve loop sites (_registry_row_for_host with registry None, get_sources_for_category (one read per call), get_shopify/algolia/jsonapi/curl_pagescrape/sitemap selectors, _direct_fetch_sources, get_gcc_shopify_pagescrape_sources_for_category, source_usage, score_source, is_render_only_domain) read _routable_registry(); explicit registry= stays unfiltered.
- rating_service: _rating_source_denied(source, link) (flag first); get_rating_tier -> 3 for a denied source under the flag; extract_rating_from_shopping skips a denied item right after the rating parse; collect_retailer_ratings skips before the dedup.
- price_service: import data_guards_v2_enabled, is_denied_url; COUNTERFEIT_BRAND_LINE_ALLOWLIST {"replica": ("margiela",)}, _CF_V2_EXTRA_TOKENS ("copycat",), _LUXURY_WHOLE_TOKEN_KEYWORDS {"lv"}, _LV_TOKEN_RE; validate_scrape_url deny (flag first, B2); is_counterfeit_listing -> _counterfeit_v2 under the flag (letters-only lookarounds, plural s/es, data-driven brand-line allowlist via _contains_token); is_luxury_brand lv whole-token under the flag. Keyword sets unchanged.
- image_service: _is_valid_image_url: base verdict, then flag + is_denied_url -> False.
- review_service: clean_review_citations._attribute and build_retailer_quotes_from_reviews skip a denied domain (flag first).
- structured_comparison_service: imports _is_valid_image_url and data_guards_v2_enabled; the Tier 1.5 piggyback in _fetch_product_data: flag ON -> through _is_valid_image_url, else the base inline test unchanged (C4).
- CLAUDE.md: the SESSION 81 D03 row after the SESSION 80 B3 row (spec 8.1 as amended: D03b URL limit, B1/B2/C4, C8 blast radius, C9 rollback wording, GC-3, the measured ON-only reds, web AND price-warmer in one window).

## Runs (every [pyt] line; summaries after ::)

```
[pyt] tag=d03g-unit-on start=2026-10-22 18:23:08 end=2026-10-22 18:23:25 elapsed=17s bound=600s status=OK rc=0 :: 250 passed, 1 warning in 12.57s
[pyt] tag=d03g-unit-off start=2026-10-22 18:23:36 end=2026-10-22 18:23:51 elapsed=15s bound=600s status=OK rc=0 :: 250 passed, 1 warning in 12.53s
[pyt] tag=d03g-pins1-off start=2026-10-22 18:24:52 end=2026-10-22 18:25:34 elapsed=42s bound=600s status=OK rc=0 :: 639 passed, 2 deselected, 11 warnings in 38.63s
[pyt] tag=d03g-pins1-on start=2026-10-22 18:25:45 end=2026-10-22 18:26:28 elapsed=43s bound=600s status=FAIL rc=1 :: 3 failed, 636 passed, 2 deselected, 11 warnings in 40.07s
[pyt] tag=d03g-pins2-off start=2026-10-22 18:26:55 end=2026-10-22 18:27:52 elapsed=57s bound=600s status=OK rc=0 :: 471 passed, 1 skipped, 13 warnings in 54.10s
[pyt] tag=d03g-pins2-on start=2026-10-22 18:28:06 end=2026-10-22 18:29:03 elapsed=57s bound=600s status=OK rc=0 :: 471 passed, 1 skipped, 13 warnings in 54.40s
[pyt] tag=d03g-comm-head-01 .. -17 (17 lines, all status=OK rc=0 except -09 status=FAIL rc=1 = the 2 baseline page_scraping nodes; full lines in pyt_lines.txt)
[pyt] tag=d03g-comm-headon-01 .. -17 (17 lines; -05 FAIL 1, -09 FAIL 2, -11 FAIL 2; full lines in pyt_lines.txt)
[pyt] tag=d03g-ci-order start=2026-10-22 19:19:49 end=2026-10-22 19:20:37 elapsed=48s bound=1200s status=OK rc=0 :: 1360 passed, 1 skipped, 2 deselected, 13 warnings in 46.82s
[pyt] tag=d03g-claude-readers start=2026-10-22 19:20:54 end=2026-10-22 19:22:44 elapsed=110s bound=1200s status=OK rc=0 :: 1289 passed, 9 skipped, 11 deselected, 35 xfailed, 13 warnings in 108.00s
[pyt] tag=d03g-mut-G1 .. G15 (16 lines, each status=FAIL rc=1 = the mutant killed; full lines in pyt_lines.txt)
```

The full 58 [pyt] lines are in pyt_lines.txt (copied from the harness ledger). netguard lines: unit 0; pins1 1 node (test_comparison_response_image_url ... api.openai.com, pre-existing); pins2 3 nodes (2 sentinel paid_route_metering, 1 egress test_algolia_catalog_stores::test_oman_sharafdg_price_zero_returns_none, in tests/.network_attempt_baseline.txt); comm: the (node, class) set is 154 at base (RED chunks) and 154 at HEAD OFF and ON, 0 head-only. hermeticity: every run "sentinel checked N test(s)" with no finding.

## Counts

- Unit: 250 nodes (143 RED + 107 PIN/GUARD) green ON and OFF.
- ON-only reds (pins1 and the whole comm set): tests/test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2; tests/test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped; tests/test_fragrance_content_quality.py::test_review_praise_no_interior_per_domain_artifact. test_review_paraphrase.py stays green ON (the review's prediction refuted, as the RED agent measured).
- Comm set: 409 files, 17 chunks. HEAD OFF 18411 passed / 2 failed / 47 skipped / 37 deselected / 37 xfailed; RED base 18134 / 145. HEAD failed = the 2 tests/test_page_scraping.py baseline nodes (in tests/.pre_impl_failures.txt). branch-only-NEW = EMPTY. ON measurement 18408 / 5 (the 2 + the 3 above).
- Mutation spot-check on the GREEN bytes: 16/16 KILLED (assertion failures), restore sha-identical, lock removed.
- Lint: ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the 9 Python files: All checks passed!; py_compile clean (cfile in a temp dir); the pre-commit hook passed at commit.

## Deviations

1. The branch feature/s81-d03-deny-and-guards already existed and was checked out at 95cf6f86 (the RED agent's notes record it), so `git checkout -b` would have failed; no git branch command was run.
2. Commit trailer names the committing agent's own model (Co-Authored-By: Claude Opus 5.5) per the common brief and the session attribution, not "Claude Fable 5.1" as the computed task text said.
3. The task names "the two RED files"; only one RED file exists (tests/test_s81_d03_deny_and_guards.py, the one hashed in the task).
4. CLAUDE.md was written BEFORE the comm run (steps 5 and 6 swapped) so the CLAUDE.md readers measure the final bytes; one wording edit after the ON measurement was followed by a re-run of all 34 CLAUDE.md readers (green).
5. The piggyback ON branch goes through image_service._is_valid_image_url as ruling C4 says; that validator strips before the scheme test, so ON a whitespace-padded page image is taken where OFF it is not (stated in the CLAUDE.md row and the PR body).
6. _counterfeit_v2 is data-driven over COUNTERFEIT_BRAND_LINE_ALLOWLIST (the prototype hard-coded "margiela"); the regex alternation is sorted deterministically (length, then text).
7. Another session's pytest (sc-s80-b4, precommit hook files) was running when I started; I ran one pytest at a time myself and did not wait for it.

## Questions for the gate / adversaries

- Q1: the registry memo is the exact ruling-B4 shape (registry, filtered); an in-place mutation of the same SOURCE_REGISTRY object is not detected (grep: nothing in app/, tests/ or scripts/ mutates it). Accept as stated limit?
- Q2: limit 5's W4-1 relabel-reason sentence (no_bh_evidence instead of global_tier with ENABLE_SHOPPING_CURRENCY_TRUTH ON) is quoted from the spec review (correction 17), not re-measured by GREEN.

## NOT MEASURED

- The full 36+ mutation table on the GREEN bytes (only the 16-mutant spot-check; the RED gate's 52-mutant table ran on the prototype). The adversaries own it.
- The comm set at base was not re-run by GREEN; the base figures are the RED agent's (comm_base_failed.txt, 17 chunks at 95cf6f86 over 407 files). The 2 files new to the set (test_scoring_service.py, test_skill_frontmatter.py) were measured at HEAD only (all green).
- The pre-commit hook test files (no .githooks change).
