# INC-I1 PICTURE-MUST-MATCH: adversary report (GREEN round), lens correctness

Lens: correctness, including the deny-list guard of I1-R1 in both ENABLE_DATA_GUARDS_V2 states, flag-OFF byte identity on every entry, the https rule on every tier and on the override for text products, and the INC-X2a [IMG_TIER] lines unchanged (GC-12). Engineering checks folded in (LC-1, one adversary). Agent: Opus 5.5 adversary of the S95-FIX lane, 2026-11-14/15.

## Verdict: SOUND (0 blocking, 0 major, 8 minors = documentation rulings for the orchestrator)

## 0. Identity and setup

- HEAD verified: `git -C sc-inc-i1 rev-parse HEAD` = 5cf13f622394f4f9133b46b026dc77376b0038b1 on fix/inc-i1-picture-must-match; `git status --short` empty at start and end.
- The eight changed files of the GREEN worktree hash to the GREEN report's 'after' column (image_relevance 5c6508fd..., image_service defc99d1..., noon c41eb965..., scs de8c77ce..., CLAUDE.md 45724a6f..., black list a56c7332..., RED A e3461440..., RED B 96153bd6...).
- Frozen RED files re-hashed at the start and the end (GREEN worktree): tests/test_inc_i1_picture_must_match.py e34614401f70599fdbd83da477b2cb19268863dee49b3a416eed4a77f9f5a08f OK; tests/test_inc_i1_noon_and_wiring.py 96153bd679ca30ee37d0232b90df9ec0f86b48be02089a2270663836a148dfb0 OK. Never edited.
- DEVIATION (scratch worktree path): `git worktree add --detach <SP>/INC-I1_adv_<lens> 5cf13f62` was refused by git (`fatal: '$GIT_DIR' too big`; the path is 273 characters, the gitdir name exceeds git's limit). Used `<SP>/INC-I1_adv_c` (detached at 5cf13f62) instead. A fresh autocrlf checkout writes CRLF into the three LF files (the leaf and the two RED files), so those three were byte-copied from the GREEN worktree; then all eight changed files were sha-verified equal to the GREEN worktree (before the probes, after every mutant restore, and before removal). The GREEN worktree was never written.
- Every pytest ran through `<SP>/harness/gate.py` on the scratch worktree, one at a time, tags inc-i1-adv-*; the ledger shows several `status=BUSY rc=126` retries (another lane-run held the mutex), each retried by gate.py, never a parallel run.

## 1. Runs ([pyt] lines; the comm-chunk / CI-order lines are taken from the runner ledger because the console line was cut by my filter)

```
[pyt] tag=inc-i1-adv-on start=2026-11-14 23:35:32 end=2026-11-14 23:35:36 elapsed=4s bound=600s status=OK rc=0   118 passed, 1 warning (ENABLE_IMAGE_RELEVANCE_GUARD=true)
[pyt] tag=inc-i1-adv-off start=2026-11-14 23:35:50 end=2026-11-14 23:35:54 elapsed=4s bound=600s status=OK rc=0   118 passed, 1 warning (=false)
[pyt] tag=inc-i1-adv-probe start=2026-11-14 23:37:37 end=2026-11-14 23:37:40 elapsed=3s bound=600s status=OK rc=0   38 passed (adversary probes Q1-Q8)
[pyt] tag=inc-i1-adv-probe2 start=2026-11-15 00:06:01 end=2026-11-15 00:06:04 elapsed=3s bound=600s status=OK rc=0   2 passed (probes Q9-Q10)
[pyt] tag=inc-i1-adv-ciorder start=2026-11-14 23:53:34 end=2026-11-14 23:53:53 status=OK rc=0 (ledger) bound=1200s   783 passed, 15 warnings
[pyt] tag=inc-i1-adv-ciorder-rev start=2026-11-15 00:02:09 end=2026-11-15 00:02:27 elapsed=18s bound=1200s status=OK rc=0   783 passed, 15 warnings
[pyt] tag=inc-i1-adv-seedzyte start=2026-11-14 23:54:00 end=2026-11-14 23:54:03 elapsed=3s bound=600s status=OK rc=0   6 passed (tests/test_seed_zyte_guard.py, see m7)
[pyt] tag=inc-i1-adv-pins start=2026-11-14 23:54:10 end=2026-11-14 23:54:50 elapsed=40s bound=1200s status=OK rc=0   1039 passed, 87 warnings
[pyt] tag=inc-i1-adv-comm-04 start=2026-11-14 23:59:14 end=2026-11-15 00:00:20 status=OK rc=0 (ledger) bound=1200s   1788 passed, 1 skipped, 7 deselected
[pyt] tag=inc-i1-adv-comm-09 start=2026-11-15 00:00:27 end=2026-11-15 00:01:27 status=OK rc=0 (ledger) bound=1200s   1400 passed, 1 skipped, 5 deselected
[pyt] tag=inc-i1-adv-comm-14 start=2026-11-15 00:01:34 end=2026-11-15 00:02:03 status=FAIL rc=1 (ledger) bound=1200s   2 failed, 3721 passed, 22 skipped
[hermeticity]/[netguard]: on/off/probe/probe2/seedzyte: 0 blocked; ciorder both orders: 3 attempts from 1 node, test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service (the known baseline node); pins: 24 attempts from 2 nodes of test_s81_s04_spend_breaker.py (sentinel host neutralized.supabase.invalid); comm-04 / -09 / -14: sentinel-host blocks only.
```

- Comm chunks 04 (test_ci_gates + test_comparison_response_image_url + 23), 09 (the five image-service suites + test_inc_g1_gate_rows + 19) and 14 (test_noon_adapter + test_page_scraping + 23) are GREEN's own chunk lists. FAILED/ERROR ids: chunk 14 = tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest and ::TestFetchPagePriceOpenGraph::test_og_meta_extraction, both in the 731bcddf base record; chunks 04 / 09: none. NEW ids vs the base record (5e2f0266..., 28 ids): NONE in every run.
- Pin set (one process, 15 files): test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py, test_start_command.py, the CLAUDE.md readers test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py, and the black-allowlist reader test_s81_s05_request_context.py: 1039 passed, no failure. The hook test files: tests/test_precommit_hook.py builds its own tmp allowlist (`.github/black-clean-paths.txt` written inside a tmp repo, :241), so the unit's allowlist edit cannot reach it; the unit edits no .githooks; not run (excluded by the rule).
- Lint (scratch, exact bytes): ruff 0.16.5 `--select E9,F63,F7,F82` on the four app files + two RED files: All checks passed; py_compile OK on the six; black 26.5.1 `--check` on the leaf + two RED files: 3 files would be left unchanged. Fresh-interpreter import of each edited module FIRST (image_relevance, noon_service, image_service, scs; a placeholder OPENAI_API_KEY name set for the two that build the client at import): all import cleanly (the leaf's module-level imports category_gate / deny_hosts / jsonld_widen -> robots_eval are stdlib-only at module level: no cycle).

## 2. Mutants on the GREEN bytes (scratch worktree; byte copy, one exact edit per site, the two RED files via gate.py, restore, sha256 compare: 29 of 29 restores OK; every kill an AssertionError)

24 spec mutants re-applied BY HAND on the GREEN code (GC-3 asks >= 8 incl. the deny-list and flag-OFF ones): the deny-list M38 M39 M40 M41 M42 M43; the flag-OFF M01 M02 M03 M05 M24 M59; the https M18 M18b M55 M58; and M04 M17 M19 M20 M22 M25 M32 M68. ALL KILLED, each by exactly the killer rows the RED report lists for the prototype (same counts, same nodes): GREEN kept every killer row meaningful. Five adversary mutants on GREEN-specific code: N6 KILLED; N1-N4 SURVIVE (minor m6).

| id | mutant | result | killing rows | pytest summary |
|---|---|---|---|---|
| M38 | deny removed from accept | KILLED | A-R17[images_source], A-R17[kg_image_url], A-R17[organic_link], A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true] | 10 failed, 108 passed, 1 warning in 3.94s |
    [pyt] tag=inc-i1-adv-mut-m38 start=2026-11-14 23:40:25 end=2026-11-14 23:40:30 elapsed=5s bound=600s status=FAIL rc=1
| M39 | image-URL deny removed from accept | KILLED | A-R17[kg_image_url], A-R17[serper_image_url] | 2 failed, 116 passed, 1 warning in 3.70s |
    [pyt] tag=inc-i1-adv-mut-m39 start=2026-11-14 23:40:37 end=2026-11-14 23:40:41 elapsed=4s bound=600s status=FAIL rc=1
| M40 | link/domain host deny removed from accept | KILLED | A-R17[organic_link], A-R17[serper_domain], A-R17[serper_link] | 3 failed, 115 passed, 1 warning in 3.72s |
    [pyt] tag=inc-i1-adv-mut-m40 start=2026-11-14 23:40:48 end=2026-11-14 23:40:52 elapsed=4s bound=600s status=FAIL rc=1
| M41 | source/title deny removed from accept | KILLED | A-R17[images_source], A-R17[serper_source] | 2 failed, 116 passed, 1 warning in 3.73s |
    [pyt] tag=inc-i1-adv-mut-m41 start=2026-11-14 23:40:59 end=2026-11-14 23:41:04 elapsed=4s bound=600s status=FAIL rc=1
| M42 | a denied organic item may open Tier 3 | KILLED | A-R19[None], A-R19[true] | 2 failed, 116 passed, 1 warning in 3.71s |
    [pyt] tag=inc-i1-adv-mut-m42 start=2026-11-14 23:41:10 end=2026-11-14 23:41:15 elapsed=4s bound=600s status=FAIL rc=1
| M43 | piggyback deny removed | KILLED | A-R17[piggyback] | 1 failed, 117 passed, 1 warning in 3.77s |
    [pyt] tag=inc-i1-adv-mut-m43 start=2026-11-14 23:41:38 end=2026-11-14 23:41:42 elapsed=4s bound=600s status=FAIL rc=1
| M01 | guard_enabled always True | KILLED | B-P01[None], B-P01[false], B-P02[None], B-P02[false], B-P06[None], B-P06[false], B-R01, A-R01, A-R16[0], A-R16[None], A-R16[false], A-R16[garbage] | 12 failed, 106 passed, 1 warning in 3.78s |
    [pyt] tag=inc-i1-adv-mut-m01 start=2026-11-14 23:41:49 end=2026-11-14 23:41:54 elapsed=4s bound=600s status=FAIL rc=1
| M02 | img _rel setup without guard_enabled() | KILLED | A-R16[0], A-R16[None], A-R16[false], A-R16[garbage] | 4 failed, 114 passed, 1 warning in 3.80s |
    [pyt] tag=inc-i1-adv-mut-m02 start=2026-11-14 23:42:00 end=2026-11-14 23:42:05 elapsed=5s bound=600s status=FAIL rc=1
| M03 | relevance_kwargs without its flag check | KILLED | B-P02[None], B-P02[false] | 2 failed, 116 passed, 1 warning in 3.79s |
    [pyt] tag=inc-i1-adv-mut-m03 start=2026-11-14 23:42:12 end=2026-11-14 23:42:16 elapsed=5s bound=600s status=FAIL rc=1
| M05 | img _rel setup without relevance is not None | KILLED | A-P02 | 1 failed, 117 passed, 1 warning in 3.86s |
    [pyt] tag=inc-i1-adv-mut-m05 start=2026-11-14 23:42:39 end=2026-11-14 23:42:44 elapsed=5s bound=600s status=FAIL rc=1
| M24 | noon block without its flag check | KILLED | B-P01[None], B-P01[false], B-R01 | 3 failed, 115 passed, 1 warning in 3.71s |
    [pyt] tag=inc-i1-adv-mut-m24 start=2026-11-14 23:42:51 end=2026-11-14 23:42:55 elapsed=4s bound=600s status=FAIL rc=1
| M59 | override https condition without the flag | KILLED | B-P06[None], B-P06[false] | 2 failed, 116 passed, 1 warning in 3.78s |
    [pyt] tag=inc-i1-adv-mut-m59 start=2026-11-14 23:43:02 end=2026-11-14 23:43:07 elapsed=4s bound=600s status=FAIL rc=1
| M18 | scheme test removed from accept and accept_pick | KILLED | A-R10, A-R11 | 2 failed, 116 passed, 1 warning in 3.76s |
    [pyt] tag=inc-i1-adv-mut-m18 start=2026-11-14 23:43:29 end=2026-11-14 23:43:34 elapsed=4s bound=600s status=FAIL rc=1
| M18b | scheme test removed from accept_scheme | KILLED | A-R11 | 1 failed, 117 passed, 1 warning in 3.66s |
    [pyt] tag=inc-i1-adv-mut-m18b start=2026-11-14 23:43:41 end=2026-11-14 23:43:45 elapsed=4s bound=600s status=FAIL rc=1
| M55 | Tier-3 raster-path test removed | KILLED | A-R21 | 1 failed, 117 passed, 1 warning in 3.66s |
    [pyt] tag=inc-i1-adv-mut-m55 start=2026-11-14 23:43:52 end=2026-11-14 23:43:56 elapsed=4s bound=600s status=FAIL rc=1
| M58 | override https condition removed | KILLED | B-R04 | 1 failed, 117 passed, 1 warning in 3.84s |
    [pyt] tag=inc-i1-adv-mut-m58 start=2026-11-14 23:44:19 end=2026-11-14 23:44:24 elapsed=5s bound=600s status=FAIL rc=1
| M04 | relevance_kwargs without the is_vision exclusion | KILLED | B-P03 | 1 failed, 117 passed, 1 warning in 3.76s |
    [pyt] tag=inc-i1-adv-mut-m04 start=2026-11-14 23:44:36 end=2026-11-14 23:44:40 elapsed=4s bound=600s status=FAIL rc=1
| M17 | Tier 1 takes the first valid image without the test | KILLED | A-R08, A-R09, A-R10, A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true], A-R24 | 11 failed, 107 passed, 1 warning in 3.85s |
    [pyt] tag=inc-i1-adv-mut-m17 start=2026-11-14 23:44:47 end=2026-11-14 23:44:51 elapsed=5s bound=600s status=FAIL rc=1
| M19 | Tier 1.5b calls the base extract under the guard | KILLED | A-R09, A-R11, A-R12, A-R17[images_source], A-R17[kg_image_url], A-R17[organic_link], A-R20, A-R24, A-R25 | 9 failed, 109 passed, 1 warning in 3.85s |
    [pyt] tag=inc-i1-adv-mut-m19 start=2026-11-14 23:45:14 end=2026-11-14 23:45:19 elapsed=5s bound=600s status=FAIL rc=1
| M20 | Tier-3 precondition removed | KILLED | A-R08, A-R13, A-R19[None], A-R19[true], A-R22 | 5 failed, 113 passed, 1 warning in 3.74s |
    [pyt] tag=inc-i1-adv-mut-m20 start=2026-11-14 23:45:26 end=2026-11-14 23:45:30 elapsed=4s bound=600s status=FAIL rc=1
| M22 | the line logs the product name as product= | KILLED | A-R08, A-R09, A-R10, A-R11, A-R12, A-R13, A-R14, A-R15, A-R17[images_source], A-R17[kg_image_url], A-R17[organic_link], A-R17[piggyback], A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true], A-R19[None], A-R19[true], A-R20, A-R21, A-R22, A-R23, A-R24, A-R25 | 27 failed, 91 passed, 1 warning in 4.09s |
    [pyt] tag=inc-i1-adv-mut-m22 start=2026-11-14 23:45:37 end=2026-11-14 23:45:42 elapsed=5s bound=600s status=FAIL rc=1
| M25 | first_https_raster returns the first URL unfiltered | KILLED | B-P05[denied_host], B-P05[http_only], B-P05[ip_host], B-P05[non_public_host], B-P05[svg], B-R02[http_then_https], A-R05 | 7 failed, 111 passed, 1 warning in 3.76s |
    [pyt] tag=inc-i1-adv-mut-m25 start=2026-11-14 23:46:05 end=2026-11-14 23:46:09 elapsed=4s bound=600s status=FAIL rc=1
| M32 | _first_image without its https preference | KILLED | A-R25 | 1 failed, 117 passed, 1 warning in 3.66s |
    [pyt] tag=inc-i1-adv-mut-m32 start=2026-11-14 23:46:16 end=2026-11-14 23:46:20 elapsed=4s bound=600s status=FAIL rc=1
| M68 | first_https_raster takes the last, not the first | KILLED | B-R01, A-R05 | 2 failed, 116 passed, 1 warning in 3.76s |
    [pyt] tag=inc-i1-adv-mut-m68 start=2026-11-14 23:46:43 end=2026-11-14 23:46:48 elapsed=4s bound=600s status=FAIL rc=1
| N1 | D-G8: override https rule applies to camera products too | SURVIVED | - | 118 passed, 1 warning in 3.14s |
    [pyt] tag=inc-i1-adv-mut-n1 start=2026-11-14 23:46:55 end=2026-11-14 23:46:59 elapsed=4s bound=600s status=OK rc=0
| N2 | D-G7: an empty category reads as non-fragrance | SURVIVED | - | 118 passed, 1 warning in 3.14s |
    [pyt] tag=inc-i1-adv-mut-n2 start=2026-11-14 23:47:05 end=2026-11-14 23:47:09 elapsed=4s bound=600s status=OK rc=0
| N3 | D-G4: https before the deny in accept | SURVIVED | - | 118 passed, 1 warning in 3.15s |
    [pyt] tag=inc-i1-adv-mut-n3 start=2026-11-14 23:47:16 end=2026-11-14 23:47:20 elapsed=4s bound=600s status=OK rc=0
| N4 | D-G5: the KG deny-only channels dropped | SURVIVED | - | 118 passed, 1 warning in 3.20s |
    [pyt] tag=inc-i1-adv-mut-n4 start=2026-11-14 23:47:43 end=2026-11-14 23:47:47 elapsed=4s bound=600s status=OK rc=0
| N6 | [IMG_TIER] guarded Tier-1 hit under another tier name | KILLED | A-R09, A-R10, A-R14, A-R24 | 4 failed, 114 passed, 1 warning in 3.80s |
    [pyt] tag=inc-i1-adv-mut-n6 start=2026-11-14 23:47:54 end=2026-11-14 23:47:58 elapsed=4s bound=600s status=FAIL rc=1

## 3. Probes (scratch-only files tests/test_zz_adv_inc_i1_probe*.py; raw results in <SP>/INC-I1_adv/probe_results.json and probe2_results.json)

- Q1 deny in BOTH ENABLE_DATA_GUARDS_V2 states: the nine frozen deny shapes (_deny_case: serper_frag / image_url / link / source / domain, kg_image_url, organic_link, images_source, piggyback) re-run with DG ON: the result is None in all nine (the frozen A-R17 covers DG OFF; A-R18 / A-R19 cover one shape each with DG ON). Log reason with DG ON: `denied` for the six text / host channels; `tier=none outcome=none candidates=0 reason=none` for kg_image_url, serper_image_url and piggyback (the base validator drops a banned image URL before the guard sees it): minor m4. Context: with the guard OFF the base cascade returns the fimgs.net or Fragrantica-sourced picture in all nine shapes (pre-existing, production today).
- Q2 the post-Phase-1 override and the deny: guard ON, DG OFF, V2 OFF, a text product, a price dict carrying an https fimgs.net page image: the override REPLACES the cascade picture (guard OFF: the same; DG ON: refused in both guard states). Minor m3.
- Q3 camera product + http page image, guard ON: the http page image replaces the cascade picture and the cascade call carries the four base keywords only (GC-5 Q-4 as ruled).
- Q4 category reading: '', None, '   ', 5 -> needs the fragrance word (other); 'FRAGRANCES' and ' Fragrances ' -> fragrances; 'electronics' -> line test only (I1-R2, GC-5 Q-3 as ruled).
- Q5 flag-OFF byte identity on EVERY entry with the knob set, for nine OFF spellings (unset, '', false, FALSE, ' 0 ', no, off, garbage, tru): guard_enabled False; relevance_kwargs == {}; get_product_image_url with `relevance` GIVEN = images[0], the bare name, num_results 1, no [IMG_RELEVANCE] line; the noon dict has no image_url key; the scs cascade call has exactly the base keywords and the base override lets an http page image through. Q5b: ' TRUE ', '1', 'yes', 'On', 'true' read ON. All pass.
- Q6 totality: a non-dict `relevance` ('junk', 5, []) or junk member types ({brand: 7, line: None, category: [], slot: True}) under the flag: no exception; product=-; the poem is rejected (fragrance_word).
- Q7 Tier-3 pick on an unrelated CDN host with a passing organic item: rejected, reason name (L-I1-13 as stated).
- Q8 scheme spelling: 'HTTPS://...' is refused by the base validator before the guard (base behaviour, candidates=0); a padded ' https://... ' is stripped and accepted.
- Q9 camera product + a noon-shaped price dict with the noon image: the override shows the noon picture (guard ON and OFF; the override itself is flag-free), and the noon adapter writes image_url under the flag whatever the caller: minor m1.
- Q10 [IMG_TIER] lines, guard ON vs OFF on the same inputs: identical (tier, outcome) sequences for a Tier-1 hit, a knowledge-graph hit and a Tier-3 hit. Organic present but none passing: OFF `llm_pick miss` (after an LLM call), ON `llm_pick skipped` and `[IMG_RELEVANCE] product=0 tier=none outcome=none candidates=0 reason=none`. The X2a grammar holds on every line (every RED row's _pairs asserts it; N6 killed): minor m5.

## 4. Claims checked against the code

- Flag-OFF identity (GREEN report 2, PR body 'OFF: byte-identical', CLAUDE.md row 'OFF'): TRUE on every entry. img: `_rel` stays None unless `relevance is not None and guard_enabled()`; every guarded condition is `_rel is None or ...`; the Tier-1 base block is the `elif`; the `finally` is a no-op for None. scs: relevance_kwargs reads the flag first and returns {}; the override condition reads the flag first. noon: the block is `if guard_enabled():`. No knob read OFF (A-R16 patches candidates_knob to raise). Module import adds only the leaf (pure frozensets). Kills: M01 M02 M03 M05 M24 M59.
- I1-R1 deny (both DG states): TRUE on every cascade tier (accept: deny before https and text, channels image URL + link/domain hosts + title/source texts + KG website/descriptionLink/descriptionSource; accept_scheme; organic_passes via _organic_reason; accept_pick on the pick URL and the related items) through the flag-free is_denied_url / is_denied_source. Q1 + M38-M43.
- https on every tier (I1-5) and on the override for text products (I1-R14): TRUE (accept, accept_scheme, accept_pick (+ raster path), override `not (isinstance(page_img, str) and page_img.strip().startswith('https://'))` under `guard_enabled() and not is_vision`). M18 M18b M55 M58 killed; B-R04 covers DG OFF and ON.
- GC-5 Q-1..Q-5: as ruled in the code (Q-1 scheme for a non-raster or page-link pick; Q-2 empty line set -> name; Q-3 empty category -> other; Q-4 text only; Q-5 deny first). Q-3 / Q-4 / Q-5 have no frozen row (m6).
- I1-R2 / R3 / R4 (a, b, c) / R5 / R7 / R10 / R12 / R16 / R18 / R20: implemented as ruled (read in `identity`, `check`, `_line_tokens`, `_host_tokens`, `candidates_knob`, `accept_pick`, FRAGRANCE_WORDS incl. the plurals and the Arabic singular + plural built from code points, EXTRA_ALIAS_GROUPS, TIER3_ORGANIC_MAX = 10).
- The [IMG_RELEVANCE] grammar (GC-6 / I1-8 / I1-R16): `product=<0|1|-> tier=<none|piggyback|search_payload|serper_images|llm_pick> outcome=<accepted|rejected|none> candidates=<int> reason=<none|scheme|brand|name|fragrance_word|denied>`, one INFO line per guarded call from the `finally` (return, exception, cancellation); closed words + one int. TRUE (A-R14, A-R15, M22 killed).
- Billing / budget: still one `try_consume_serper_image_credit(1)` per call and one `search_images` call; num_results = the knob (I1-R15 stated limit). No refund / quota surface touched (R-A3 not engaged: no abstain, no refusal, no envelope).
- Contract freeze (PLAN_S80 section 0): no key removed, renamed or retyped; under the flag `products[i].image_url` is an https URL or None for text products; the noon `image_url` rides the public price view (spec OQ-11 measured it; not in the PR body: m2).
- L-I1-10 'the L2 row never stores it': TRUE (product_data_service.save_price builds an explicit field list without image_url, :336-361).
- The PR body's proof backing log lines exist: `[PRICE] BH adapter direct hit for %s ... via %s` (scs:7895), `[L2.6] Phase 1 race timeout for %s` (scs:6317), `[BUDGET] serper_images daily budget exhausted` (api_budget_service:1288).
- 'with an empty brand (every app compare while INC-R1 is OFF)': consistent with the D1 diagnosis (the explicit-pair builder sets brand '').
- Counts: 118 nodes = RED 29 functions / 99 nodes + PIN 10 functions / 19 nodes (A: r01-r25 + p01-p04; B: r01-r04 + p01-p06; r03 = 55 nodes) TRUE. numstat +569/+128-6/+15/+10/+7-2/+3/+1529/+489 = 2750 / 8 TRUE. High-byte counts of the edited files unchanged (72 / 186 / 2876 / 3904 / 15); no bare LF in a CRLF file; the leaf and the RED files LF with 0 bytes > 127; the two rewritten CLAUDE.md lines (:313, :341) are pure insertions (old line = prefix + suffix of the new line); the only non-ASCII added lines are those two (pre-existing characters). Added-line sweep: no 8-digit run, @gmail, +973, sk-, AKIA, JWT, PEM, credentialed URL or 64-hex literal. PR body 23,583 B (<= 25,600).
- Footprint (GC-9): exactly the eight files; scs +15 = one import (+comment), one keyword expression (+comment), the I1-R14 condition (+comment); no client / migration / requirements / price_service / jsonld_widen / category_gate / router edit. The 8 deleted lines are each a base line rewritten into its guarded form (image_service 6, CLAUDE.md 2). Untouched as claimed: _is_valid_image_url, extract_image_from_search, extract_image_via_gpt, _TIER3_PROMPT, the X2a bookkeeping and the CancelledError arm (A-P03 / A-P04 pin two of them).

## 5. Comm set (re-derived independently)

- My derivation: an AST import graph of app/ (reverse closure of the four seeds: 13 modules incl. app.main, response_builder, url_extraction_service, kb_serve, kb_operator, the three route modules) UNION app.main / TestClient users UNION source scanners UNION CLAUDE.md / CLAUDE_MD readers UNION .github readers, MINUS test_precommit_hook*.py. GREEN's 712 (text-mention closure of 85 app modules) is a superset of mine except: tests/conftest.py (not a test file), test_be_harness.py, test_eval_runner.py, test_cron_eval_nightly.py (comment / docstring mentions only, no import of a closure module), ten files matched only by my over-wide word 'main' (they call a script's main(), never app.main), and tests/test_seed_zyte_guard.py (m7). Then every scripts/ module importing an edited module was listed (bias_matrix_probe, cron_compare_judge, cron_warm_price_cache, measure_warmed_kpi, seed_zyte_luxury, warm_kpi_truth) and every test naming one of them checked: all are members except tests/test_bias_matrix_probe.py (the script names app.main only in its docstring: not a member) and tests/test_seed_zyte_guard.py (m7, measured green: 6 passed).
- No MISSING member by the union rule as written. The named source-scanning pins, both CLAUDE.md readers by the import graph and the black-allowlist reader are in the 712 and passed in my pin set.

## 6. Findings

BLOCKING: none. MAJOR: none.

- m1 (camera path, Q9): the noon block in noon_service._confirm_pdp is caller-agnostic, so under the flag a CAMERA compare priced by a fresh noon fetch (or by an L1 noon entry written while ON) shows the noon JSON-LD picture through the base override (V2 OFF; the override is not text-gated for page images that pass https). The CLAUDE.md row and PR L-I1-14 say 'the camera path is unchanged (no guard, no https rule)'; the parenthetical is true, 'unchanged' is not. Production today: no camera compare reaches the override while vision is off. Ruling: restate L-I1-14 (or gate the noon picture to text compares in a later unit).
- m2 (response delta, doc only): under the flag the noon image_url rides products[i].price / overview.products[i].price into the response through price_service.public_price_view (every non-underscore key). Additive, flag-gated, unread by both bundles, no client schema validation, the Zyte-seed precedent; the spec measured it (OQ-11) but the PR body and the CLAUDE.md row do not say it. One sentence.
- m3 (override deny, DG OFF, Q2): with the guard ON and ENABLE_DATA_GUARDS_V2 OFF (production mix) an https page image on a banned host still replaces the cascade picture through the post-Phase-1 override (measured with fimgs.net); only the producers keep banned hosts out (noon: allowed_image_url denies them; a cached Zyte-seed image_url is the only other producer). Out of I1-1 scope (the override's policy is unchanged except I1-R14), but the in-cascade piggyback deny/https the docs cite is unreachable from scs (page_scrape_image=None at the one call site). State it.
- m4 (DG ON log reason, Q1): with ENABLE_DATA_GUARDS_V2 ON a banned image URL is dropped by the base validator before the guard, so the kg_image_url / serper_image_url / piggyback denials log 'tier=none outcome=none candidates=0 reason=none' instead of 'denied' (the result is None in all nine shapes in both states). I1-R1's 'the reason word is denied' holds for DG OFF on that channel; note it for the canary reason mix.
- m5 ([IMG_TIER] semantics, Q10): under the guard, organic results present but none passing gives '[IMG_TIER] tier=llm_pick outcome=skipped' (base: 'miss' after an LLM call) and organic_passes counts nothing, so a call refused only there logs 'tier=none outcome=none candidates=0 reason=none', indistinguishable from 'nothing to test'. The X2a grammar is unchanged (GC-12 holds); the meaning of skipped widens. Add to the canary items.
- m6 (unpinned ruled behaviours): four GREEN behaviours survive every frozen row: N1 the GC-5 Q-4 camera exemption ('and not is_vision' in the override), N2 the GC-5 Q-3 empty category -> other, N3 the GC-5 Q-5 deny-before-https order in accept, N4 the D-G5 knowledge-graph website / descriptionLink / descriptionSource deny channels. GREEN disclosed N1 / N2 (L-G3) and D-G4 / D-G5. Production effect: N2 unreachable (scs passes canonical keys), N3 changes only the logged reason, N1 camera-only, N4 a KG card whose only banned trace is its description link. LC-4: stated limits, or gate rows at the orchestrator's choice.
- m7 (comm set, scripts hop): tests/test_seed_zyte_guard.py imports scripts/seed_zyte_luxury.py whose main() imports structured_comparison_service (function level, :214) and is in neither the 712 nor the 710 base set (both closures walk app/ only). Not a member by the literal union rule (its text names no edited module) and measured green at HEAD by the adversary (tag inc-i1-adv-seedzyte, 6 passed); the other five scripts importing an edited module are reached by members already. Recommend the closure follow scripts/ in later units.
- m8 (wording / coupling): the leaf calls the PRIVATE deny_hosts._registrable_label (and reads jsonld_widen.RASTER_EXTENSIONS); the CLAUDE.md row says 'the flag-free deny_hosts match functions'. A rename of the private helper would make _host_tokens raise AttributeError under the flag (the 'every function total' docstring claim then fails; gather turns it into image None). Also the PR body lists A-P02 and B-P03 (flag ON rows: no identity / a camera product) among the flag-OFF identity pins: they pin the no-identity entries, not flag OFF.

## 7. Prove-nothing rows

None of the 118 frozen rows is vacuous: every RED row failed at base on an AssertionError (RED report) and every flag-OFF PIN runs with the knob set and a call / order recorder (B1). Observation: A-P01 (flag unset, no relevance) is killed by no mutant in either table: by construction the guard is unreachable there (`relevance is not None` short-circuits), so it pins only the base path, incl. GREEN's `if` -> `elif` restructure of Tier 1 (D-G9), which no mutant exercised. A-P03 / A-P04 pin unchanged shared helpers (no mutant targets them). B-P04 pins the base override branches with the flag unset.

## 8. End state

- GREEN worktree sc-inc-i1: HEAD 5cf13f62, `git status --short` empty, frozen RED hashes OK (end re-hash). Scratch worktree removed with `git worktree remove --force` and absent from `git worktree list` (see the return). Mutation lock created and removed in the scratch worktree only.
- Not done: no push, no PR, no commit, no edit of the GREEN worktree; the full jest suite and the fourteen client fences were not re-run (GREEN ran the fences as the last gate; LC-7 puts the full suite in the last round); no production claim (H6): nothing here proves the phone result.
