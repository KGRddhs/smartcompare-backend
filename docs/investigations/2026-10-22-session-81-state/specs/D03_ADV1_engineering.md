# D03 DENY-AND-GUARDS: adversary report, engineering lens

- Unit: D03 (`ENABLE_DATA_GUARDS_V2`, default OFF). Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-d03`, branch `feature/s81-d03-deny-and-guards`.
- HEAD verified at the start and at the end: `5244f7165dbde49579a9f4147229b20050427c18`. The worktree's `git status --short` was empty both times. Base: `95cf6f864b4e70980ca191daa064c0118e223c13`.
- RED file `tests/test_s81_d03_deny_and_guards.py`, sha256 `ae8fffc7ffe50205af9170a82f1de22ca38e629482b1afc93bf1c0181610449c`. I hashed it at the start and at the end, on both the working copy and the HEAD blob: MATCH each time. I never edited it.
- Scratch worktree: `<scratchpad>/D03_adv_engineering`, created with `git worktree add --detach` at 5244f716.
  - It had no node_modules junction.
  - I checked it by sha256. The 8 edited CRLF files were identical to the unit worktree. The two new LF files are CRLF in the scratch checkout because of autocrlf; with CR stripped they give the exact committed shas.
  - I removed it with `git worktree remove --force`. `git worktree list` no longer shows it.
- Notes, logs and scripts: `<scratchpad>/D03_adv/`. That covers notes.md, every `*.log`, `probe*.json`, `mutation_results_e.json`, `derive_comm.out`, `my_comm_set.txt`, `bytes_check.txt` and the chunk lists.
- Mutation lock: I created `.qa-mutation.lock` in the scratch worktree only and removed it afterwards. Every restore matched its sha.

## Verdict: NOT_READY (0 blocking, 1 major, 9 minors)

## MAJOR

**MAJ-E1: the Shopping door has no deny. The CLAUDE.md row and the PR body state limit 5 falsely.**

This confirms the correctness adversary's MAJ-1 independently. The measurement is mine.

What limit 5 claims, in the CLAUDE.md row and the PR body:
- With the flag ON, the "as if absent" `registry_tier` None is harmless, because "the never-fetched chokepoint of item 2 keeps it unfetched".
- With `ENABLE_SHOPPING_CURRENCY_TRUTH` ON, a Fragrantica Shopping link's W4-1 relabel reason "reads `no_bh_evidence` instead of `global_tier`".

Why that is wrong: Serper Shopping rows are never fetched. Their price comes straight from the payload, so the `validate_scrape_url` chokepoint does not cover them. `price_service.extract_price_from_shopping` and `_shopping_bh_host_evidence` (price_service.py:10117-10265) never consult `deny_hosts`.

Measured with probe3 (`[pyt] tag=d03ae-probe3 ... status=OK rc=0`, `probe3.json`). Setup: `ENABLE_SHOPPING_CURRENCY_TRUTH=true`, ask BHD, and one Shopping row with source "Fragrantica".

| link | flag OFF | flag ON |
|---|---|---|
| `https://www.fragrantica.com/bh-en/perfume/...` | `source_method=converted_usd`, reason `global_tier`, `registry_tier` `global` | `source_method=local_bhd` (GENUINE), no reason, `registry_tier` None (the `/bh-en` first segment is BH evidence for an off-registry host) |
| plain fragrantica.com path | `converted_usd` / `global_tier` | `converted_usd` / `no_bh_evidence` (the row's claim holds only here) |

In both flag states the price ships with `retailer: "Fragrantica"` and a fragrantica.com `url`. With the flag ON, a banned host is therefore shown as a price, and on a BH-locale path it gets a genuine label. This is the B2 / RC1 class: "as if absent" turns a fail-closed refusal into a downgrade, this time on the door that ruling B2's chokepoint does not cover. The scs `_seed_shortcircuit_candidates` stash is the same door; the correctness adversary names it.

Fix belongs to the orchestrator's FIX1 ruling, for example: with the flag ON, the Shopping door (both `extract_price_from_shopping` and the stash mirror) drops a row whose link or source is denied. Then rewrite limit 5 in the row and the PR body, and add a RED row and a G row for the `/bh-en` Shopping case.

## MINORS (documentation and rulings)

**MIN-E1. Stale line anchor.** The CLAUDE.md row cites "the `source_router.py:347` fragrantica literal row". At HEAD that row is at :349: the deny_hosts import added two lines above it, so :347 is the base line. Cite it by name or as :349.

**MIN-E2. "Only deny literal list" overclaims.** The row and the deny_hosts docstring both say "`DENY_HOSTS` is the only deny literal list in `app/`, pinned". In fact:
- `LEGACY_DESCRIPTOR_DENY_HOSTS` is a second deny literal tuple in `app/`, in the same module.
- R1i (`test_r1i_single_deny_literal_list`) skips `deny_hosts.py` entirely.

So the pin proves "no second list outside deny_hosts.py", not more. The wording needs to match.

**MIN-E3. Wrong reason in PR body section 4.1.** The PR body explains `tests/test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped` as "expects a quote from a cited Fragrantica result". The test actually asserts `quotes[0]["retailer"] == "basenotes.net"` (snippet 2, :143). It goes red ON because Basenotes is denied, not Fragrantica.

**MIN-E4. The row's stated limits drop three spec or review limits:**
- Spec L10. With the flag ON, the global fragrance discovery window holds 3 domains instead of 4. Measured: `site:amazon.com OR site:sephora.com OR site:walmart.com` against the OFF list plus `site:fragrantica.com`, in both catalog states.
- Review correction 18. `LVs Neverfull` is luxury at base and not ON.
- Spec L8. "inspired" / "generic" / "alternative" / "vintage" titles still drop as whole words; the row narrows this to "Homage" only.

Side note for the correctness adversary's MIN-4: probe1 measured `is_luxury_brand("Salvatore Ferragamo Uomo")` True OFF (the `lv` inside "salvatore") and False ON. So with the flag ON a real luxury house loses the luxury bit. That supports reading the "never inside ... Salvatore" text as describing a new false negative, not a false positive that was cleared.

**MIN-E5. "Flag read FIRST" is not pinned.**
- Hand mutant XD6 swaps `data_guards_v2_enabled() and is_denied_url(url)` to `is_denied_url(url) and data_guards_v2_enabled()` in `validate_scrape_url`. It survives all 250 nodes (`[pyt] tag=d03ae-mut-XD6 ... status=OK rc=0`).
- It is behaviourally equivalent because every `is_denied_*` function is pure and never raises. The "flag first" code comments and the PR body's "the FIRST statement of every gated predicate" are therefore code shape, not pinned behaviour.
- The PR body also overclaims: `validate_scrape_url`, `get_rating_tier`, `is_counterfeit_listing`, `is_luxury_brand` and `_is_valid_image_url` all run a base precondition before the flag (the correctness adversary's MIN-6).

Ruling: either accept it as equivalent, or soften the wording.

**MIN-E6. Black ratchet not followed.** `.github/black-clean-paths.txt` says "Added a new .py file? It should be black-clean, so add it here". `black 26.5.1 --check` would reformat both new files (`app/services/deny_hosts.py` and the RED file), and neither is listed. CI does not enforce this, and recent units (B1, B3, S78) skipped the ratchet too. House-rule ruling.

**MIN-E7. URL parser differential.** `is_denied_url` uses `urlsplit`:
- `https://fragrantica.com\@evil.test/` reads as host `evil.test` and returns False, while WHATWG parsers (browser and RN image loaders) resolve it to `fragrantica.com`.
- `https://evil.test\@fragrantica.com/` returns True.

The list is a policy list, not a security boundary, and `url_validator` uses the same parser. This is a stated-limit candidate (measured in probe1 `urls`).

**MIN-E8. D03b / D03c / D03d not in the ledger yet.** R-D03-2 says D03c is "recorded in DEFECT_LEDGER". The session-81 `DEFECT_LEDGER.md` still holds only its 3-line header. This is an orchestrator item.

**MIN-E9. Private-name import.** `structured_comparison_service` imports the private `image_service._is_valid_image_url` by name, on a second `from app.services.image_service import` line. A test that patches `image_service._is_valid_image_url` does not reach the scs binding. This is style only; ruling C4 asked for the routing.

## Engineering checks (all measured)

**Diff hygiene** (`bytes_check.txt`):
- 1719 lines added and 15 removed. Every removed line is a replaced `SOURCE_REGISTRY` loop header, the descriptor literal, the image return or the piggyback `if` (all justified).
- 0 non-ASCII added lines.
- The 7 edited CRLF backend files plus CLAUDE.md have 0 bare LF in the working copy, 0 CR in the HEAD blobs, and bytes > 127 identical at base, HEAD and working copy (CLAUDE.md 3961 / 3961, price_service 5590 / 5590, ...).
- New files: LF, 0 bytes > 127.
- `git diff --check`: clean. No whole-file diff.
- Added-line sweep (gmail, +973, 8-digit runs, sk-, AKIA, xox, JWT, PEM, credentialed URL): 0 hits. The 31 http literals are all in the test file or the moved image line.
- The commit author is the repo's standing git identity (same as earlier commits). Co-Authored-By: Claude Opus 5.5.

**New imports.** Every one is covered by the spec change list or a ruling:
- price_service: `is_denied_url` (B2).
- review_service (B1).
- scs: `_is_valid_image_url` and `data_guards_v2_enabled` (B2 / C4).
- deny_hosts imports only the stdlib: os, re, typing, urllib.parse.
- A wider ruff pass (F401, F811, F841) over the 7 edited files at base vs HEAD: 30 vs 30, 0 head-only.

**Lint:**
- `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` on the 9 Python files: "All checks passed!".
- `py_compile` on all 9: clean.

**Comm set re-derived with the union rule** (`derive_comm.py`, all depths under tests/, 707 test files):
- My rule set is 419 files. GREEN's set is 409.
- Every GREEN file is in my set (0 GREEN-only).
- The 10 files in mine but not GREEN's came only from my wider "reads app/" regex. I checked each one by hand: all of them read only unedited files (auth_routes.py, scoring_service.py, prompt_personalities.py, extraction_service.py, apple_siwa_service.py, openai_service via getsource), or nothing under app/. None reads or walks an edited file, so none is a rule miss.
- No edited test-support module, so the support-module importer addendum adds nothing.
- Result: **no missing file**.
- Node arithmetic checks out. The 2 files new versus RED's 407 hold 134 nodes. Base (RED) 18134 passed + 145 failed = 18279; HEAD 18411 + 2 = 18413; the difference is 134. Skipped 47, xfailed 37 and deselected 37 are equal on both sides.

**Runs:** unit file OFF and ON, three comm chunks OFF and ON (chosen by touched surface), the CI-order set, the source-scanning / manifest / CLAUDE.md-reader chunk, and one hook-file half. Every `[pyt]` line is in the section below.
- The comm-chunk failures are only the 3 measured ON-only reds.
- Every netguard node seen is already in `tests/.network_attempt_baseline.txt` (0 new).
- No hermeticity finding.

**Runtime truth of the row and PR-body claims** (probe1 `probe.json`, probe2 `probe2.json`):
- Discovery: `site:fragrantica.com` is gone ON in both catalog states.
- `score_source(fragrantica url)` goes 1.0 -> 0.5; `registry_tier` goes `global` -> None.
- `_routable_registry() is SOURCE_REGISTRY`: OFF True, ON False.
- `validate_scrape_url(fragrantica url)`: OFF True, ON False.
- Calvin Klein: the 18 BHD floor and the designer bit go from True OFF to False ON.
- `get_rating_tier`: Fragrantica, fragrantica.com and Fragrantica.ru go 2 -> 3. Parfumo and Basenotes are 3 in both states. Boots stays 2.
- Gold set (400 names): exactly 1 counterfeit delta (frag-018) and exactly 5 luxury deltas (hair-005/010/012, supp-021, fash-015). These match the row and PR body.
- Host table: fragrantica.cn, parfumo.it, parfumo.co, fimgs.network, fr.fragrantica.com, `fragrantica.com:443` and `FRAGRANTICA.COM.` are True. notfragrantica.com, fragrantica.com.evil.test, evil-fragrantica.com and fragrantica-evil.com are False.
- None of the five public functions raised on None, int, bytes, list, "", whitespace, NUL, "http://", `http://[::1` or `http://%zz`.
- The descriptor tuple identity holds.
- `strict_title_match` has 11 importing modules besides price_service (the row's "11 modules" is right).
- `COUNTERFEIT_KEYWORDS` has 21 entries and `LUXURY_BRAND_KEYWORDS` 29.
- The PR table's parametrisation counts match `--collect-only` (P1 16, P3 8, P4 8, P6 15 = 11 + 4, P9 8, P9b 3, P11 8, P12 8, P13 8, R2a 5, R2b 3, R3a 40, R6a 8, R7a 4, R9b 8; 250 total).
- The ON-only reds are exactly the 3 named nodes in my chunks, and `test_review_paraphrase.py` stays green ON, as the PR body says.
- The direct `SOURCE_REGISTRY` readers named in limit 6 exist under exactly those roles.
- Every caller of `probe_search_descriptor` catches the refusal (`resolve_search_descriptors.resolve_hosts`, and `search_descriptor_service` at :280).
- Every `_registry_row_for_host` caller outside the module passes no `registry=`, so the filter applies to all of them.

**Contract freeze, error handler, billing.** No response key is added, removed or retyped. `get_rating_tier` keeps the int contract (3). `error_handler.py`, `url_*` and the billing paths are untouched (P14). With the flag OFF, every response is byte-identical per the green P rows, the FY25 digests (`test_s75_fanout_identity`), the W4-13 ledger and the B5 adapter files, which I re-ran in chunks B and C.

**Mutants** (hand block-moves XD1-XD7 for this unit plus 3 engineering spec mutants), each on a sha-verified byte copy and restored by sha:
- KILLED: XD1, XD2, XD3, XD4, XD5, XD7, M10, M35, M36 (M36 is also killed by T7b in `test_legal_docs_u8.py`).
- SURVIVED as an equivalent: XD6 (MIN-E5).

## Every [pyt] line

```
[pyt] tag=d03ae-unit-off start=2026-10-22 20:36:17 end=2026-10-22 20:36:22 elapsed=5s bound=600s status=OK rc=0   (250 passed; netguard 0; hermeticity 250)
[pyt] tag=d03ae-unit-on start=2026-10-22 20:36:31 end=2026-10-22 20:36:36 elapsed=5s bound=600s status=OK rc=0    (250 passed; netguard 0)
[pyt] tag=d03ae-commA-off start=2026-10-22 20:44:32 end=2026-10-22 20:45:18 elapsed=46s bound=1200s status=OK rc=0 (534 passed; [netguard] blocked 22 attempt(s) from 5 node(s), all 5 in the baseline)
[pyt] tag=d03ae-commA-on start=2026-10-22 20:46:14 end=2026-10-22 20:46:57 elapsed=44s bound=1200s status=OK rc=0 (534 passed; netguard 5 nodes, 0 new)
[pyt] tag=d03ae-commB-off start=2026-10-22 20:47:22 end=2026-10-22 20:48:25 elapsed=63s bound=1200s status=OK rc=0 (827 passed, 1 deselected; netguard 0)
[pyt] tag=d03ae-commB-on start=2026-10-22 20:48:47 end=2026-10-22 20:49:58 elapsed=71s bound=1200s status=FAIL rc=1 (3 failed = test_fragrance_content_quality.py::test_review_praise_no_interior_per_domain_artifact, test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2, test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped; 824 passed; netguard 1 node, 0 new)
[pyt] tag=d03ae-commC-off start=2026-10-22 20:50:21 end=2026-10-22 20:51:34 elapsed=72s bound=1200s status=OK rc=0 (1563 passed, 1 skipped; netguard 6 nodes, 0 new)
[pyt] tag=d03ae-commC-on start=2026-10-22 20:51:52 end=2026-10-22 20:53:17 elapsed=85s bound=1200s status=OK rc=0 (1563 passed, 1 skipped; netguard 6 nodes, 0 new)
[pyt] tag=d03ae-ci-order start=2026-10-22 20:53:39 end=2026-10-22 20:55:37 elapsed=118s bound=1200s status=OK rc=0 (48 files sorted; 1360 passed, 1 skipped, 2 deselected; netguard 4 nodes, 0 new)
[pyt] tag=d03ae-pins-readers start=2026-10-22 20:58:09 end=2026-10-22 21:03:48 elapsed=339s bound=1200s status=OK rc=0 (25 files: test_ci_gates, test_behavior_dimension_translation, test_start_command, test_legal_docs_u8(+_polish), test_legal_disclosure_s77, test_legal_s78, test_migration_index_predicate_immutability, test_migration_037/041/042/043, test_delete_user_cascade, test_consent_capture_w3_16, test_s79_b3b_apple_revoke, test_sqlfluff_config, test_security_regression, test_be_harness, test_hermeticity_pins, test_domain_s76, test_events_allowlist_superset, test_skill_frontmatter, test_w4_13_measurement_truth, test_u3c_store_false_pin, test_model_config; 1273 passed, 4 deselected; netguard 27 nodes, 0 new)
[pyt] tag=d03ae-hook-collect start=2026-10-22 21:04:27 end=2026-10-22 21:04:33 elapsed=6s bound=600s status=OK rc=0 (327 hook nodes collected)
[pyt] tag=d03ae-probe start=2026-10-22 21:06:46 end=2026-10-22 21:07:01 elapsed=16s bound=600s status=OK rc=0
[pyt] tag=d03ae-probe2 start=2026-10-22 21:08:35 end=2026-10-22 21:08:45 elapsed=10s bound=600s status=OK rc=0
[pyt] tag=d03ae-mut-XD1 start=2026-10-22 21:15:04 end=2026-10-22 21:15:12 elapsed=8s bound=600s status=FAIL rc=1  (KILLED: test_p2_registry_never_mutated, test_r3c_per_call_flip, test_r3d_routable_registry_identity)
[pyt] tag=d03ae-mut-XD2 start=2026-10-22 21:15:12 end=2026-10-22 21:15:18 elapsed=6s bound=600s status=FAIL rc=1  (KILLED: test_r7e_scs_piggyback_skips_denied_on)
[pyt] tag=d03ae-mut-XD3 start=2026-10-22 21:15:19 end=2026-10-22 21:15:39 elapsed=20s bound=600s status=FAIL rc=1 (KILLED: test_g11b_denied_bh_locale_link_never_harvested[true], test_r11a_validate_scrape_url_denies_on)
[pyt] tag=d03ae-mut-XD4 start=2026-10-22 21:15:41 end=2026-10-22 21:16:00 elapsed=20s bound=600s status=FAIL rc=1 (KILLED: test_r4a_rating_tier_denied_on)
[pyt] tag=d03ae-mut-XD5 start=2026-10-22 21:16:01 end=2026-10-22 21:16:09 elapsed=8s bound=600s status=FAIL rc=1  (KILLED: 8 nodes, test_r2a_descriptor_deny_on[...], ...)
[pyt] tag=d03ae-mut-XD6 start=2026-10-22 21:16:09 end=2026-10-22 21:16:26 elapsed=16s bound=600s status=OK rc=0   (SURVIVED, equivalent: 250 passed)
[pyt] tag=d03ae-mut-M35 start=2026-10-22 21:16:27 end=2026-10-22 21:16:59 elapsed=32s bound=600s status=FAIL rc=1 (KILLED: test_r1b_module_is_stdlib_only)
[pyt] tag=d03ae-mut-M36 start=2026-10-22 21:17:00 end=2026-10-22 21:17:28 elapsed=29s bound=600s status=FAIL rc=1 (KILLED: test_legal_docs_u8.py::test_t7b_external_hosts_and_clients_map_to_manifest, test_r1c_no_http_literal_t7b_safe)
[pyt] tag=d03ae-mut-M10 start=2026-10-22 21:17:29 end=2026-10-22 21:17:35 elapsed=6s bound=600s status=FAIL rc=1  (KILLED: 10 nodes, test_p4_descriptor_off_equals_base[...], ...)
[pyt] tag=d03ae-mut-XD7 start=2026-10-22 21:17:37 end=2026-10-22 21:17:46 elapsed=10s bound=600s status=FAIL rc=1 (KILLED: test_r4f_collect_retailer_ratings_drops_denied)
[pyt] tag=d03ae-unit-collect start=2026-10-22 21:18:58 end=2026-10-22 21:19:00 elapsed=1s bound=600s status=OK rc=0
[pyt] tag=d03ae-new2-collect start=2026-10-22 21:19:18 end=2026-10-22 21:19:21 elapsed=3s bound=600s status=OK rc=0 (134 collected: test_scoring_service.py + test_skill_frontmatter.py)
(d03ae-hooks-notdash: 167 nodes, bound 1800; no [pyt] line. I killed my own tree (tag and cwd matched) at 21:41 after about 72 passes and 0 F. At about 14 s per node under the sibling B4 load it would have exceeded the 1800 s bound.)
[pyt] tag=d03ae-probe3 start=2026-10-22 21:42:51 end=2026-10-22 21:42:59 elapsed=8s bound=600s status=OK rc=0
[pyt] tag=d03ae-hooks-r2-notdash start=2026-10-22 21:43:17 end=2026-10-22 21:47:11 elapsed=234s bound=560s status=OK rc=0 (tests/test_precommit_hook_round2.py -k "not dash": 15 passed, 15 deselected)
```

## Mutants (hand block-moves for D03 plus engineering spec mutants)

| id | edit | result |
|---|---|---|
| XD1 | `_routable_registry`: the memo hit moved above the flag read | KILLED (p2, r3c, r3d) |
| XD2 | scs piggyback: the base inline branch first, the flag branch as `elif` | KILLED (r7e) |
| XD3 | `validate_scrape_url`: the deny block moved past the final return | KILLED (g11b[true], r11a) |
| XD4 | `get_rating_tier`: the deny check moved below the RATING_TIER_2 loop | KILLED (r4a) |
| XD5 | `search_descriptor_service._deny`: the flag branch moved past the legacy return | KILLED (r2a x5 and more) |
| XD6 | `validate_scrape_url`: `is_denied_url(url) and flag` (order swap) | SURVIVED, equivalent (MIN-E5) |
| XD7 | `collect_retailer_ratings`: the deny skip removed | KILLED (r4f) |
| M10 | descriptor `DENY_HOSTS = deny_hosts.DENY_HOSTS` | KILLED (p4 x10) |
| M35 | `import requests` in deny_hosts | KILLED (r1b) |
| M36 | an https fragrantica literal in deny_hosts | KILLED (r1c and T7b) |

## NOT MEASURED

- Hook test files, except `test_precommit_hook_round2.py -k "not dash"` (15 of 327 nodes). The full non-dash run was stopped at about 43% with 0 failures. Under the current box load, the dash half and the remaining files cannot fit the bound and the budget.
  - Why it matters little: `.githooks` is unchanged, and the brief excludes these files unless a unit edits `.githooks`. The committed bytes already passed the hook at commit time.
- The comm set at base. I did not re-run it: every HEAD failure in my chunks is an ON-only red already named, and the OFF chunks had 0 failures, so no branch-only-NEW node exists to re-check at base.
- The 14 comm chunks I did not choose. GREEN's 17-chunk HEAD run reports only the 2 `.pre_impl_failures.txt` page_scraping nodes.
- The correctness-lens mutation table (M1-M34). That belongs to the correctness adversary.

## git status

- `sc-s81-d03`: empty at the start and at the end (HEAD 5244f716).
- Scratch worktree: removed.
