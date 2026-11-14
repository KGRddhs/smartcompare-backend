# S95-DEP adversary report (one adversary, LC-1 SAFE; correctness lens + supply-chain checks)

- Unit: worktree sc-s95-dep, branch fix/s95-dep-dnspython-soupsieve, HEAD 15492072125bf9b90f972ee4785827925cff1daf, base 731bcddf531a7e123963246168ca19f262859337 (= HEAD~1 = merge-base), git status --short empty (verified at start and after the uv compile).
- Window: 2026-11-14 20:01 to 20:56 AST. Nothing installed, nothing written into the worktree, no git write.
- VERDICT: SOUND. Blocking: none. Major: none. Four minors, all stated limits (section M).

## C1 diff footprint: PASS
- diff --stat / --numstat base..HEAD: requirements.in 6/1, requirements.txt 5/3; nothing else.
- requirements.txt: only `dnspython==2.9.0 -> 2.9.2` and `soupsieve==2.9.2 -> 4.1` (its via comment grows `-r requirements.in`). Parsed pins: runtime 71 vs 71, exactly those two changed; requirements-dev.txt 53 vs 53, none changed.
- requirements.in: the floor `dnspython>=2.9.0 -> >=2.9.2`, the new direct floor `soupsieve>=4.0`, four comment lines. Added lines are pure ASCII. `git diff --check` is clean. Blobs are LF with 0 CR bytes. The personal-value and credential-shape sweep of the added lines finds nothing. The BOM and em dash at the top of requirements.in were already there.

## C2 lock currency, as CI runs it: PASS
- I copied both committed locks into the notes folder and ran the two CI commands from W with uv 0.12.5, writing to the copies (seeded): `uv pip compile requirements.in -o <copy> --universal --python-version 3.12 --quiet` (rc 0) and `uv pip compile requirements-dev.in -o <dev copy> -c requirements.txt --universal --python-version 3.12 --quiet` (rc 0).
- CI's `grep -v '^#'` diff against the committed blobs: EMPTY for both (diff rc 0 / 0).

## C3 pip-audit: PASS
- HEAD venv `python -m pip_audit -r W/requirements.txt --strict`: `No known vulnerabilities found`, rc 0 (37.7 s).
- Cause reproduced on the base lock: exactly 5 findings, rc 1. dnspython 2.9.0 CVE-2026-128089 (fix 2.9.2); soupsieve 2.9.2 CVE-2026-126192 (2.10.0), CVE-2026-126190 (4.0.0), CVE-2026-126193 (3.0.2), CVE-2026-126191 (3.0.2).
- Floor sufficiency: the HEAD lock with soupsieve==4.0 is also clean (rc 0), so `>=4.0` / `>=2.9.2` are real floors.
- Reachability, from the PyPI advisory texts: the four soupsieve advisories need :has(~), descendant combinators, nested pseudo-classes, or an attacker-supplied selector string. The dnspython advisory needs zone-file WKS parsing. None of these is reachable from the app: 8 constant compound selectors, and dns is never imported (C5). The bump exists to unblock the CI gate, not to close a live exposure.

## C4 release facts (PyPI JSON, read-only): PASS
- dnspython 2.9.2: wheel + sdist uploaded 2026-11-03T23:56Z, not yanked, requires_python >=3.11. There is a 2.9.1 in between (2026-10-29).
- soupsieve 4.1: 2026-11-10T01:59Z, not yanked, requires_python >=3.11.5. Also 4.0 (2026-11-03T14:28Z) and 4.0.1 (2026-11-04), neither yanked. 3.0 and 3.0.1 are YANKED (skipped by the lock); 3.0.2 is the first 3.x that requires >=3.11.5. The official changelog already lists an unreleased 4.1.1 (perf fixes); PyPI latest is 4.1.
- Python 3.12: runtime.txt is python-3.12.9, CI is 3.12, both venvs are 3.12.9; every requires_python above is satisfied.
- beautifulsoup4 4.15.0 (2026-06-07, not yanked) requires_dist `soupsieve>=1.6.1` with no upper bound, and `typing-extensions>=4.0.0`. It predates soupsieve 3.0, so compatibility was measured (C5 and C6), not assumed.
- email-validator 2.3.0 requires `dnspython>=2.0.0`.

## C5 compatibility: PASS, with two edge-case semantic changes (minor M2)
- CSS selector users: only app/services/price_service.py, in the iHerb path (`_iherb_card_currency_token` and `fetch_iherb_price._w04_parse_block`). Eight calls: L16522 `meta[itemprop="priceCurrency"]`, L16667 `a[data-ga-brand-name][data-ga-discount-price][title]`, L16721 `div.product-inner`, L16722 `meta[itemprop="price"]`, L16732 `a[href*="/pr/"]` and `a[title]`, L16734 `[itemprop="name"]`, L16750 `[data-rating]`.
- The other bs4 users (url_extraction_service, the rest of price_service, scripts/measure_*.py) never call select. No other installed distribution imports soupsieve; bs4/css.py imports it when bs4 is imported.
- All eight are compound selectors (type, class, attribute presence, `=` and `*=`) with no combinator and no pseudo-class.
- Changelog items 2.10 to 4.1 that touch this grammar:
  - 4.0 BREAK: template contents are no longer part of the document.
  - 4.1 FIX: `[attr=value]` no longer ignores a trailing newline in the value.
  - 4.1: `[attr*=value]` quadratic-time fix (performance only).
  - 4.0: the ASCII case-insensitive attribute list (rel, method, lang, dir...) excludes itemprop, title, href and data-*.
  - 2.10: no coercion of non-string attribute values (parsed HTML gives strings).
  - The 3.0 BREAKs (:has strictness, custom-selector order) and the 3.0.3 `>` fix are not used.
  - Nothing the selectors use was removed.
- Measured (sel_eval.py run with each venv; bs4 4.15.0 both; soupsieve 2.9.2 vs 4.1):
  - IDENTICAL on a normal synthetic page: 26 result keys, including upper-case tags and attributes, padded class, empty values and missing meta.
  - IDENTICAL on all 11 tests/fixtures/iherb_*.html.
  - IDENTICAL on the iframe-wrapped, leading-space and tab/CR edges.
  - DIFFERENT on cards inside <template>: 2.9.2 matches them, 4.1 finds 0 cards.
  - DIFFERENT on itemprop values with a trailing newline: 2.9.2 matches `price&#10;`, 4.1 does not.
- Performance: 1500 cards plus a 400-deep chain, 10500 matches both. Best 0.248 s (2.9.2) vs 0.238 s (4.1), so no regression.
- Bonus: 4.1 fixes a selector-compile race between threads ("bogus syntax error or silently parse a selector incorrectly"). The iHerb block runs on the price-parse pool (ENABLE_PRICE_PARSE_OFFLOAD, ON per the session-79 facts), so 4.1 is the better pick over 4.0.x.
- dnspython: no direct import in app/, scripts/ or tests/. No installed distribution except email_validator imports dns. pydantic 2.13.4 calls `email_validator.validate_email(email, check_deliverability=False)`, and email-validator 2.3.0 imports dns only for deliverability.
  - Measured in both venvs: sys.modules holds no dns.* after `import email_validator` or after EmailStr validation.
  - 12 synthetic EmailStr cases (valid, IDN, padded, bad, reserved TLDs, IP literal) give IDENTICAL results.
  - The 2.9.1 and 2.9.2 changes (resolver query ids, negative-TTL cap, DNSSEC, tokenizer CRLF, LOC/TTL parsing, WKS bound) sit in modules the app never loads. EmailStr fields: app/api/auth_routes.py L97/L126/L145/L164.

## C6 tests: PASS (new_at_head EMPTY)
- Set: `git grep -l` over HEAD tests/*.py for price_service|url_extraction_service|bs4|BeautifulSoup|email_validator|EmailStr (238 files), plus auth_routes with register|login (32). Union 263, no test_precommit_hook*.
- Minus the 4 non-test support modules (conftest.py, _env_safety.py, _hermeticity.py, w4_11_prompt_digest_recorder.py; they hold no test_ items and load anyway): 259 files (runset.txt), chunk_00..chunk_10 (25 x10 + 9).
- Same chunks, same worktree bytes: base via pyt.py (.venv-qaren), head via pyt_s95dep.py (argv shows .venv-s95-dep). The HEAD venv equals the head locks exactly. The BASE venv equals the base locks plus 3 stray packages (backoff, distro, posthog) that no lock lists and no code imports; the results were identical, so no confound showed.
- Per chunk, the counts, skips, xfails, warnings, netguard and hermeticity lines are identical at base and head (pyt_lines.txt).
- Failed nodes, the same 6 on both sides:
  - 2 test_auth_interceptor nodes, listed in tests/.pre_impl_failures.txt (red by choice).
  - 4 CRLF-hygiene nodes that read the Windows CRLF working copy: test_s81_s07_meas_harness::test_r35_fixtures, test_s81_s19_gap_queue::test_r15_hygiene, test_s81_s24_auth_throttle::test_r92_hygiene and ::test_p83_red_file_setenv_hygiene.
  - comm -13 (head only) is EMPTY, and so is comm -23.
- Extras outside the defined set, same both sides:
  - chunk_11: the 3 iHerb-referencing files the grep missed (test_adapter_prefetch_hook, test_iherb_scraping [live_unit, deselected], test_price_source). 21 passed, 5 deselected.
  - chunk_12: the 9 test files that read requirements*.in/txt (test_ci_gates, test_start_command, test_sqlfluff_config...). 224 passed, 1 skipped.

## C7 public-repository review: PASS with minors
- The commit title and body, and the requirements.in comment, are ASCII and match the measured facts:
  - five advisories and their CVE ids;
  - "fix 2.9.2, released 2026-11-03" and "all fixed by 4.0, released 2026-11-03" are correct in UTC;
  - "requirements-dev.txt is unchanged" is confirmed by C2.
- Trailer: Co-Authored-By Claude Opus 5.5. No personal values and no credential shapes.
- Floors only, in the established certifi / #367 / S81-06 pattern; the exact pins live in the lock. The lock carries no hashes (pre-existing, out of scope).
- The requirements.txt working copy in W is LF (`git ls-files --eol`: w/lf) while the other requirement files are CRLF. The index is LF for all and status is clean, so there is no effect on the commit (observation only).

## M minors (stated limits)
- M1 release age.
  - CLAUDE.md L752 (Harness facts): "Pin new dependencies to a release at least 14 days old."
  - At the commit (2026-11-14T17:00Z), soupsieve 4.1 is 4.6 days old and dnspython 2.9.2 is 10.7 days old.
  - No CVE-fixing release of either package is 14 days old (soupsieve 4.0 is 11.1 days, 4.0.1 is 10.0 days). The rule can only be met by leaving pip-audit --strict red.
  - Literally the rule covers NEW dependencies, and neither package is new to the lock (soupsieve is only newly direct).
  - The commit does not acknowledge the exception. Recommendation: state it in the PR body and keep 4.1, because of the thread-race fix in C5.
- M2 two-major jump semantics.
  - soupsieve 4.0 no longer matches inside <template>, and 4.1 no longer lets `[itemprop="price"]` match a value with a trailing newline. Both change iHerb card capture on such markup.
  - Neither markup appears in the 11 iHerb fixtures. Live iHerb markup was not verifiable here (no network beyond the granted docs).
  - If it ever occurs, the GA and microdata selectors return 0 cards and the path falls through to the existing fallback chain.
  - The commit body does not mention the 3.0 / 4.0 BREAK items; the PR body should carry this compatibility statement.
- M3 the commit body's "five advisories were published after #404" was not verified: advisory publication dates are outside the granted sources.
- M4 environment limits.
  - Local uv 0.12.5 and the dev-locked pip-audit, on Windows; CI installs the newest uv and pip-audit on Linux, against a live advisory feed.
  - Base runs used the HEAD worktree bytes (by design). Tests that read the requirements files therefore saw the HEAD files in both runs; chunk_12 shows them green.
  - The BASE venv carries 3 stray packages.
  - The 6 known failures are environmental or red by choice, and identical on both sides.

## Runner lines
[pyt] tag=s95d-adv-base0 start=2026-11-14 20:11:29 end=2026-11-14 20:11:57 elapsed=28s bound=1200s status=FAIL rc=1 | 2 failed, 816 passed, 25 warnings in 26.76s | [netguard] blocked 23 attempt(s) from 9 node(s) | [hermeticity] sentinel checked 818 test(s)
[pyt] tag=s95d-adv-head0 start=2026-11-14 20:14:35 end=2026-11-14 20:15:09 elapsed=34s bound=1200s status=FAIL rc=1 | 2 failed, 816 passed, 25 warnings in 31.99s | [netguard] blocked 23 attempt(s) from 9 node(s) | [hermeticity] sentinel checked 818 test(s)
[pyt] tag=s95d-adv-base1 start=2026-11-14 20:19:36 end=2026-11-14 20:20:11 elapsed=35s bound=1200s status=OK rc=0 | 1790 passed, 1 skipped, 2 deselected, 1 xfailed, 15 warnings in 33.53s | [netguard] blocked 0 attempt(s) from 0 node(s) | [hermeticity] sentinel checked 1792 test(s)
[pyt] tag=s95d-adv-head1 start=2026-11-14 20:21:54 end=2026-11-14 20:22:36 elapsed=42s bound=1200s status=OK rc=0 | 1790 passed, 1 skipped, 2 deselected, 1 xfailed, 15 warnings in 40.15s | [netguard] blocked 0 attempt(s) from 0 node(s) | [hermeticity] sentinel checked 1792 test(s)
[pyt] tag=s95d-adv-base2 start=2026-11-14 20:23:26 end=2026-11-14 20:24:52 elapsed=86s bound=1200s status=OK rc=0 | 2111 passed, 20 warnings in 84.75s (0:01:24) | [netguard] blocked 72 attempt(s) from 37 node(s) | [hermeticity] sentinel checked 2111 test(s)
[pyt] tag=s95d-adv-head2 start=2026-11-14 20:25:21 end=2026-11-14 20:26:58 elapsed=97s bound=1200s status=OK rc=0 | 2111 passed, 20 warnings in 95.51s (0:01:35) | [netguard] blocked 72 attempt(s) from 37 node(s) | [hermeticity] sentinel checked 2111 test(s)
[pyt] tag=s95d-adv-base3 start=2026-11-14 20:27:12 end=2026-11-14 20:27:29 elapsed=17s bound=1200s status=OK rc=0 | 540 passed, 1 skipped, 1 xfailed, 16 warnings in 16.26s | [netguard] blocked 2 attempt(s) from 2 node(s) | [hermeticity] sentinel checked 542 test(s)
[pyt] tag=s95d-adv-head3 start=2026-11-14 20:27:41 end=2026-11-14 20:28:01 elapsed=19s bound=1200s status=OK rc=0 | 540 passed, 1 skipped, 1 xfailed, 16 warnings in 17.69s | [netguard] blocked 2 attempt(s) from 2 node(s) | [hermeticity] sentinel checked 542 test(s)
[pyt] tag=s95d-adv-base4 start=2026-11-14 20:28:12 end=2026-11-14 20:28:35 elapsed=23s bound=1200s status=OK rc=0 | 3469 passed, 2 skipped, 2 warnings in 21.88s | [netguard] blocked 7 attempt(s) from 1 node(s) | [hermeticity] sentinel checked 3471 test(s)
[pyt] tag=s95d-adv-head4 start=2026-11-14 20:29:04 end=2026-11-14 20:29:28 elapsed=25s bound=1200s status=OK rc=0 | 3469 passed, 2 skipped, 2 warnings in 22.78s | [netguard] blocked 7 attempt(s) from 1 node(s) | [hermeticity] sentinel checked 3471 test(s)
[pyt] tag=s95d-adv-base5 start=2026-11-14 20:29:58 end=2026-11-14 20:30:28 elapsed=30s bound=1200s status=OK rc=0 | 1006 passed, 24 skipped, 21 warnings in 28.40s | [netguard] blocked 147 attempt(s) from 18 node(s) | [hermeticity] sentinel checked 1006 test(s)
[pyt] tag=s95d-adv-head5 start=2026-11-14 20:31:15 end=2026-11-14 20:31:46 elapsed=31s bound=1200s status=OK rc=0 | 1006 passed, 24 skipped, 21 warnings in 29.52s | [netguard] blocked 147 attempt(s) from 18 node(s) | [hermeticity] sentinel checked 1006 test(s)
[pyt] tag=s95d-adv-base6 start=2026-11-14 20:31:58 end=2026-11-14 20:34:25 elapsed=147s bound=1200s status=OK rc=0 | 1109 passed, 1 skipped, 17 warnings in 145.65s (0:02:25) | [netguard] blocked 8 attempt(s) from 3 node(s) | [hermeticity] sentinel checked 1109 test(s)
[pyt] tag=s95d-adv-head6 start=2026-11-14 20:34:38 end=2026-11-14 20:37:06 elapsed=148s bound=1200s status=OK rc=0 | 1109 passed, 1 skipped, 17 warnings in 146.36s (0:02:26) | [netguard] blocked 8 attempt(s) from 3 node(s) | [hermeticity] sentinel checked 1109 test(s)
[pyt] tag=s95d-adv-base7 start=2026-11-14 20:38:23 end=2026-11-14 20:40:44 elapsed=142s bound=1200s status=FAIL rc=1 | 2 failed, 3632 passed, 67 warnings in 139.55s (0:02:19) | [netguard] blocked 24 attempt(s) from 2 node(s) | [hermeticity] sentinel checked 3634 test(s)
[pyt] tag=s95d-adv-head7 start=2026-11-14 20:41:27 end=2026-11-14 20:44:05 elapsed=158s bound=1200s status=FAIL rc=1 | 2 failed, 3632 passed, 67 warnings in 154.93s (0:02:34) | [netguard] blocked 24 attempt(s) from 2 node(s) | [hermeticity] sentinel checked 3634 test(s)
[pyt] tag=s95d-adv-base8 start=2026-11-14 20:45:07 end=2026-11-14 20:45:45 elapsed=39s bound=1200s status=FAIL rc=1 | 2 failed, 1373 passed, 19 warnings in 37.28s | [netguard] blocked 12 attempt(s) from 6 node(s) | [hermeticity] sentinel checked 1375 test(s)
[pyt] tag=s95d-adv-head8 start=2026-11-14 20:46:04 end=2026-11-14 20:46:44 elapsed=40s bound=1200s status=FAIL rc=1 | 2 failed, 1373 passed, 19 warnings in 38.43s | [netguard] blocked 12 attempt(s) from 6 node(s) | [hermeticity] sentinel checked 1375 test(s)
[pyt] tag=s95d-adv-base9 start=2026-11-14 20:46:54 end=2026-11-14 20:47:37 elapsed=43s bound=1200s status=OK rc=0 | 1119 passed, 7 skipped, 21 warnings in 42.13s | [netguard] blocked 29 attempt(s) from 11 node(s) | [hermeticity] sentinel checked 1126 test(s)
[pyt] tag=s95d-adv-head9 start=2026-11-14 20:48:05 end=2026-11-14 20:48:49 elapsed=43s bound=1200s status=OK rc=0 | 1119 passed, 7 skipped, 21 warnings in 42.00s | [netguard] blocked 29 attempt(s) from 11 node(s) | [hermeticity] sentinel checked 1126 test(s)
[pyt] tag=s95d-adv-base10 start=2026-11-14 20:49:19 end=2026-11-14 20:49:26 elapsed=7s bound=1200s status=OK rc=0 | 463 passed, 10 skipped, 1 warning in 6.00s | [netguard] blocked 0 attempt(s) from 0 node(s) | [hermeticity] sentinel checked 473 test(s)
[pyt] tag=s95d-adv-head10 start=2026-11-14 20:49:27 end=2026-11-14 20:49:34 elapsed=7s bound=1200s status=OK rc=0 | 463 passed, 10 skipped, 1 warning in 6.25s | [netguard] blocked 0 attempt(s) from 0 node(s) | [hermeticity] sentinel checked 473 test(s)
[pyt] tag=s95d-adv-base11 start=2026-11-14 20:50:45 end=2026-11-14 20:50:55 elapsed=10s bound=1200s status=OK rc=0 | 21 passed, 5 deselected in 8.85s | [netguard] blocked 12 attempt(s) from 2 node(s) | [hermeticity] sentinel checked 21 test(s)
[pyt] tag=s95d-adv-head11 start=2026-11-14 20:50:56 end=2026-11-14 20:51:05 elapsed=10s bound=1200s status=OK rc=0 | 21 passed, 5 deselected in 8.80s | [netguard] blocked 12 attempt(s) from 2 node(s) | [hermeticity] sentinel checked 21 test(s)
[pyt] tag=s95d-adv-base12 start=2026-11-14 20:52:05 end=2026-11-14 20:52:28 elapsed=22s bound=1200s status=OK rc=0 | 224 passed, 1 skipped, 15 warnings in 21.16s | [netguard] blocked 0 attempt(s) from 0 node(s) | [hermeticity] sentinel checked 225 test(s)
[pyt] tag=s95d-adv-head12 start=2026-11-14 20:52:28 end=2026-11-14 20:52:50 elapsed=22s bound=1200s status=OK rc=0 | 224 passed, 1 skipped, 15 warnings in 19.81s | [netguard] blocked 0 attempt(s) from 0 node(s) | [hermeticity] sentinel checked 225 test(s)

Artifacts (notes folder): notes.md, runset.txt, chunk_00..chunk_12, base*/head*.log, base_failed.txt, head_failed.txt, sel_eval.py, sel_base.json, sel_head.json, sel_cmp.txt, dns_path.py, dns_base.json, dns_head.json, audit_head.txt, audit_base.txt, audit_floor.txt, lc_req.txt, lc_dev.txt, pypi_facts.txt, vulns.txt, web/ss_changelog.txt, web/dns_whatsnew.txt.
