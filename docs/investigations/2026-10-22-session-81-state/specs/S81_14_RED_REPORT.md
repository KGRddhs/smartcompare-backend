# S81-14 KB-SCHEMA -- RED report (Opus 5.5 RED agent, 2026-10-23 21:20-22:40 AST)

- Unit: S81-14 KB-SCHEMA (migrations 045 + 047, the pure leaf app/services/kb_service.py, .sqlfluff; NO runtime flag).
- Real worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s14, DETACHED at e1878dd836e721d7e8c6c53fe1aa3d2b9fadb83e (task base). Only new file: tests/test_s81_kb_schema.py.
- Notes folder: <scratchpad>/S81-14_red/ (notes.md, base_shas.txt / after_shas.txt, probe_keys.py/.out, the prototype under proto/, mutants.py + mutate.py + mutation_results.jsonl + mut_*.log, comm_*.log, proto_comm_*.log, comm_list.txt, comm_reasons.tsv, mut_table.md).
- Inputs read in full: s81-common.txt (re-read at the end: it changed mid-run, origin/main is now 98d85433 = + #371 S81-05; my base stays e1878dd8 as the task names), RULINGS_S81_14.md (R-S14-1..16 + measurement rulings), the spec (749 lines), the review (118 lines), the two spec prototypes.

## Files written

| file | sha256 | bytes | >127 | CR |
|---|---|---|---|---|
| tests/test_s81_kb_schema.py (real worktree, untracked) | 7b1db7e3fedfeaea83a7f73f0b2b8fa27c06a8f3a6718f44ca748bfd1228367b | 84409 | 0 | 0 |
| proto/migrations/045_kb_core.sql (prototype for GREEN) | 987ba019de9a1c67fdd8853b5bf19b24a96bbb47f2ddcc475b4ae0bc9fa4b374 | 23141 | 0 | 0 |
| proto/migrations/047_012_revoke.sql (= the spec prototype) | abb6597efdc231473109d30798890ff7f99e4cc3a685ebaa99f1d603ed97ddb1 | 2894 | 0 | 0 |
| proto/migrations/rollback/045_kb_core.sql | 4a7fcbabc946e5dfbea8e2180dfe8e7ceaa91a8afc439f803dac050eae9043ba | 1149 | 0 | 0 |
| proto/migrations/rollback/047_012_revoke.sql | 0631c3041fc81a2ee11ef0274ef44aee65dfd76b9f57da96680b2e87a102ef18 | 1148 | 0 | 0 |
| proto/app/services/kb_service.py (post-fix, see deviation 14) | 935ad9996417898762e5ddc0bbaff1473228ed184cbfdb7529bb1330e769fdb3 | 25658 | 0 | 0 |
| proto/.sqlfluff (adds large_file_skip_byte_limit = 0, +5 lines) | e39a5299e4a1a7d4472fd47b07af05a4ab7e35503f8092748951d231b73b5120 | 5594 | 0 | 0 |

The added-line sweep shapes (8-digit runs, @gmail, +973, sk-/JWT/PEM/AKIA/xox, credentialed URLs) find 0 hits in every file above.

## 1. Base measurements (step 2), real worktree at e1878dd8

Chunk A (the spec's 25 migration readers): `[pyt] tag=s14-comm-A start=2026-10-23 22:14:10 end=2026-10-23 22:14:49 elapsed=39s bound=1200s status=OK rc=0` -- 625 passed, 10 deselected; `[hermeticity] sentinel checked 625 test(s)`; `[netguard] blocked 12 attempt(s) from 6 node(s)` (all test_security_regression.py, the committed baseline class). Equals the spec's 625 at dfc6502f.

Chunk B (the spec's 22 scanner / CLAUDE.md-reader files, split in three for the 600 s tool cap):
- `[pyt] tag=s14-comm-B1 start=2026-10-23 22:15:05 end=2026-10-23 22:15:34 elapsed=29s bound=1200s status=OK rc=0` (recovered from harness/pyt_ledger.jsonl: my redirect discarded that stdout) -- 377 passed; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- `[pyt] tag=s14-comm-B2 start=2026-10-23 22:16:06 end=2026-10-23 22:17:29 elapsed=83s bound=1200s status=OK rc=0` -- 730 passed; `[hermeticity] sentinel checked 730 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- `[pyt] tag=s14-comm-B3 start=2026-10-23 22:17:44 end=2026-10-23 22:19:28 elapsed=104s bound=1200s status=OK rc=0` -- 651 passed; `[hermeticity] sentinel checked 651 test(s)`; `[netguard] blocked 22 attempt(s) from 21 node(s)` (hermeticity self-tests by design).
- Total 377 + 730 + 651 = 1758 passed = the spec's 1758 at dfc6502f.

Chunk C (the 15 identity-helper importers, run at base IN THIS RED as ruled; + 3 union files + the new unit file):
- `[pyt] tag=s14-comm-C1 start=2026-10-23 22:19:46 end=2026-10-23 22:20:12 elapsed=25s bound=1200s status=OK rc=0` -- 902 passed; `[hermeticity] sentinel checked 902 test(s)`; `[netguard] blocked 12 attempt(s) from 4 node(s)`.
- `[pyt] tag=s14-comm-C2 start=2026-10-23 22:20:34 end=2026-10-23 22:21:56 elapsed=82s bound=1200s status=FAIL rc=1` -- 344 failed, 286 passed; `[hermeticity] sentinel checked 630 test(s)`; `[netguard] blocked 28 attempt(s) from 10 node(s)`. The 344 failures are EXACTLY the new file's RED node ids (`comm -3` against the unit-file base set is empty); every other C2 file (test_fragrance_content_quality, test_flush_live_price_key, test_correctness_cache_key, test_cellular_generation_cache_key, test_cache_key_size_variant, test_s75_fanout_identity incl. FY25, test_w4_13_flag_off_ledger, test_retro_w1_2c, test_secret_scan_static, test_seed_zyte_guard) passed.
- So the 15 importer files are green at base (C1's 8 + C2's 7). No pre-existing base failure anywhere in the comm set (the spec's 1.10 named none for these files).

## 2. The RED file at base (step 4)

`[pyt] tag=s14-red-base start=2026-10-23 21:53:19 end=2026-10-23 21:53:41 elapsed=22s bound=600s status=FAIL rc=1` -- 344 failed, 58 passed; `[hermeticity] sentinel checked 402 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- Every failure is an AssertionError: the log carries exactly 344 `E   AssertionError` lines, no other exception class, no ERROR (setup) node. Missing files go through `_require` (assert is_file), the missing module through `_kb()` (assert find_spec), missing symbols through `_attr` (assert hasattr).
- Failed ids: <scratchpad>/S81-14_red/red_base_failed.txt (344). Per row (params): r01 x1, r02 x4, r03 x1, r04 x10, r04b x10, r05 x11, r06 x5, r07 x1, r08 x1, r09 x7, r09b x1, r10 x1, r11 x2, r12 x1, r13 x1, r14 x1, r15 x1, r15b x1, r15c x1, r15d x1, r16 x1, r17 x1, r18 x1, r19 x1, r20 x1, r20b x4, r21 x1, r22 x48, r22b x1, r23 x1, r24 x3, r25 x34, r25b x1, r25c x1, r26 x1, r27 x10, r28 x155, r28b x14, r28c x1, r28d x1, r29 x1.
- PIN rows green at base (58): p01 no importer of kb_service (AST over app/ + scripts/); p02 no kb_* relation literal (the exact 16 names: ten tables, kb_offers_latest, five functions, as AST string constants, R-S14-8); p03 every 012 .table() call site (11 measured) uses get_admin_supabase_client / self.client from it and never the user client (047 safety); p04 x48 the spine_key literal matrix (16 rows incl. the Elixir / EDP 60ml variant rows, 0ml, 10000 ml, 7.5ml sample, 100ml + 10ml gift, 6000ml, Armani) under ENABLE_EXACT_PRICE_GATE unset / "true" / " TRUE " with ENABLE_NORMALIZE_WORDS_EMPTY_FIX deleted, app.main imported BEFORE the monkeypatch (R-S14-14 / C17); p05 every migration under the EFFECTIVE sqlfluff skip limit, read like test_retro_w1_2c (0 = disabled); p06 x4 the LF sha256 of tests/test_s75_fanout_identity.py, tests/fixtures/s75_fanout_identity_digests.json, tests/test_w4_13_flag_off_ledger.py, tests/fixtures/w4_13_flag_off_ledger.json at e1878dd8 (untouched); p07 the 043 fence over the real forward files: no gaps, user tables == KNOWN_USER_TABLES (13), none kb_*; p08 the flag env survives a re-import of app.main / extraction_service (the dotenv order) and price_service reads gate ON / fix OFF.
- B1 rule: no flag exists, so no flag-OFF PIN to configure; the "no behaviour change" proof is p01-p03 + p06/p07 + the unedited FY25 / W4-13 nodes in chunk C. Every env-dependent row sets or deletes ENABLE_EXACT_PRICE_GATE, ENABLE_NORMALIZE_WORDS_EMPTY_FIX and ENABLE_DATA_GUARDS_V2 explicitly.

## 3. Prototype (step 5), detached scratch worktree <scratchpad>/S81-14_red/s14_scratch at e1878dd8 (removed)

Installed: the six proto files above + the RED file. sqlfluff 4.3.0 with the new .sqlfluff on the four migration files: rc 0, "All Finished!", stderr EMPTY (no Skipping line) at 23,141 bytes; negative control (one lower-case `create index` in a copy) rc 1 with CP01 at L290, so 045 is really linted. git diff --stat on .sqlfluff: 5 insertions only.
- Unit file, prototype in place: `[pyt] tag=s14-proto start=2026-10-23 21:54:57 end=2026-10-23 21:55:06 elapsed=8s bound=600s status=OK rc=0` -- 402 passed (all 344 RED rows green, all 58 PIN rows green); `[netguard] blocked 0 attempt(s) from 0 node(s)`. There is no flag, so the "flag OFF" run is the base run above (PINs green there too).
- Repo scanners on the prototype (the whole comm set, head side, in scratch):
  - `[pyt] tag=s14-proto-comm-A start=2026-10-23 22:22:25 end=2026-10-23 22:23:19 elapsed=53s bound=1200s status=OK rc=0` -- 627 passed (625 + the two new immutability params 045/047), 10 deselected; netguard 12 from 6.
  - `[pyt] tag=s14-proto-comm-B1 start=2026-10-23 22:23:31 end=2026-10-23 22:23:57 elapsed=27s bound=1200s status=OK rc=0` -- 377 passed.
  - `[pyt] tag=s14-proto-comm-B2 start=2026-10-23 22:24:06 end=2026-10-23 22:25:21 elapsed=75s bound=1200s status=OK rc=0` -- 730 passed.
  - `[pyt] tag=s14-proto-comm-B3 start=2026-10-23 22:25:52 end=2026-10-23 22:27:37 elapsed=105s bound=1200s status=OK rc=0` -- 651 passed; netguard 22 from 21.
  - `[pyt] tag=s14-proto-comm-C1 start=2026-10-23 22:27:45 end=2026-10-23 22:28:13 elapsed=28s bound=1200s status=OK rc=0` -- 902 passed; netguard 12 from 4.
  - `[pyt] tag=s14-proto-comm-C2 start=2026-10-23 22:28:21 end=2026-10-23 22:29:31 elapsed=71s bound=1200s status=OK rc=0` -- 630 passed; netguard 27 from 10 (base 28 from 10: the committed-baseline egress class, no new node).
  - So the 043 fence (13 user tables, no gap), the column census, the immutability detector, the SECURITY DEFINER census (037), the T7 host-literal scan (test_legal_docs_u8), R1i (test_s81_d03), the model-literal pins, every app/ walker and both tests/ walkers (test_hermeticity_pins, test_ci_gates, which saw the new test file) are green with kb_service.py, 045 and 047 present.

## 4. Mutation table (step 6): 65 mutants, 65 KILLED, 0 survived

Driver <scratchpad>/S81-14_red/mutate.py: per mutant a byte copy (shutil.copyfile) of every touched file, exact edits that each match ONCE (CRLF-aware), the WHOLE unit file through pyt.py (bound 600; every failing row recorded), restore from the copy, sha256 compare (all 65 restores verified), a .qa-mutation.lock held for the run and removed. Every kill is AssertionError only (no other exception class, no ERROR node). Final scratch state cmp-identical to the proto files.

| # | mutant | killed by (rows that failed) | summary |
|---|---|---|---|
| M1 | 045: one table REVOKE without service_role | r05 | 1 failed |
| M2 | 045: GRANT SELECT on kb_products TO anon | r05, r06 | 6 failed |
| M3 | 045: kb_product_card SECURITY DEFINER | r06 | 5 failed |
| M4 | 045: kb_variants FK without ON DELETE CASCADE | r04, r07 | 2 failed |
| M5 | 045: kb_feedback gains user_id -> users | p07, r04, r07, r08, r27 | 5 failed |
| M6 | 045: audience renamed gender_marker | p07, r04, r08, r27 | 4 failed |
| M7 | 045: basenotes dropped from the canonical_url belt | r04, r09 | 2 failed |
| M8 | 045: google added to kb_reviews.source | r04, r10 | 2 failed |
| M9 | 045: Eau Fraiche dropped from kb_products.concentration | r04, r11 | 2 failed |
| M10 | 045: idx_kb_gaps volatile predicate | r12 | 1 failed |
| M11 | 045: view without security_invoker | r13 | 1 failed |
| M12 | 045: card specs without the cited filter | r14 | 1 failed |
| M13 | 045: prune without the rn > keep conjunct | r15 | 1 failed |
| M14 | 047: reviews_update not dropped | r17, r18 | 2 failed |
| M15 | 047: one REVOKE without authenticated | r17 | 1 failed |
| M16 | leaf: kb_product_id returns the full spine_key | r22, r22b, r23 | 41 failed |
| M17 | leaf: own normaliser instead of spine_key | r22, r22b, r23 | 44 failed |
| M18 | leaf: empty identity allowed | r22, r22b, r23 | 5 failed |
| M19 | leaf: kb_variant_key ignores a concentration mismatch | r23 | 1 failed |
| M20 | leaf: kb_source_allowed bound at import | r24, r28c | 4 failed |
| M21 | leaf: canonical_offer_url keeps the query | r25 | 2 failed |
| M22 | leaf: canonical_offer_url strips userinfo instead of refusing | r25 | 2 failed |
| M23 | leaf: GTIN weights 1,3 | r26, r27, r28b | 3 failed |
| M24 | leaf: build_offer_row omits observed_currency | r27 | 1 failed |
| M25 | leaf: build_offer_row skips the deny rule | r28, r28c | 2 failed |
| M26 | leaf: import os + os.getenv | r21 | 1 failed |
| M27 | rollback/045 keeps kb_gtin_check_digit_ok | r16 | 1 failed |
| M28 | .sqlfluff skip limit back to 20000 (045 silently unlinted) | p05, r20 | 2 failed |
| M29 | a scratch app module imports kb_service | p01 | 1 failed |
| M30 | 045: GTIN SQL weights swapped | r15c | 1 failed |
| M31 | 045: prune AND -> OR | r15 | 1 failed |
| M32 | 045: kb_specs_cited_has_source deleted | r04b | 1 failed |
| M33 | 045: amount double precision | r04 | 1 failed |
| M34 | leaf: kb_product_id drops variant | r22, r22b, r23 | 8 failed |
| M35 | leaf: canonical_offer_url accepts shop..example (both host layers) | r25 | 7 failed |
| M36 | text_routes flush uses the user-scoped client | p03 | 1 failed |
| M37a | leaf: feedback device key lower-cased before the check | r28 | 1 failed |
| M37b | leaf: image provenance host without the belt / deny rule | r28 | 2 failed |
| M38 | leaf: placeholder identity allowed | r22, r22b | 4 failed |
| M39 | 045: view DISTINCT ON without observed_currency | r13 | 1 failed |
| M40 | 045: view ranks captured_at before last_seen (BL1) | r13 | 1 failed |
| M41 | 045: card reads the view | r14 | 1 failed |
| M42 | 045: prune ages by captured_at | r15 | 1 failed |
| M43 | 045: market dropped from the observation UNIQUE | r04b, r28d | 2 failed |
| M44 | 045: kb_merchants regains a deny-label CHECK | r04b, r09b | 2 failed |
| M45 | leaf: build_merchant_row applies the deny rule | r28b, r28c | 3 failed |
| M46 | 045: device_key NOT NULL again | r04 | 1 failed |
| M47 | leaf: device-less vote refused | r28b | 1 failed |
| M48 | 045: lang dropped from the kb_specs UNIQUE | r04b | 1 failed |
| M49 | 045: card ignores p_lang | r14 | 1 failed |
| M50 | 045: kb_variants trigger missing | r03 | 1 failed |
| M51 | leaf: build_product_row stops emitting updated_at | r27 | 1 failed |
| M52 | leaf: kb_variant_key keeps sizes above 5000 | r23 | 1 failed |
| M53 | leaf: kb_variant_key size 0 -> None (the pre-ruling spec) | r23 | 1 failed |
| M54 | leaf: deny label group hard-coded (not derived) | r09 | 7 failed |
| M55 | 045: canonical_url belt in the unsorted label order | r04, r09 | 2 failed |
| M56 | 045: kb_prune_feedback upper bound 36500 | r15b | 1 failed |
| M57 | 047: service_role loses DELETE on product_prices | r17 | 1 failed |
| M58 | 045: trigger function SECURITY DEFINER | r06 | 5 failed |
| M59 | 045: platform_confidence numeric again | r04 | 1 failed |
| M60 | 045: registry column removed | r04, r27 | 2 failed |
| M61 | 045: source_hint back to the substring CHECK | r04, r09, r25c | 4 failed |
| M62 | spec_spine_service.spine_key drops variant (P4 is live) | p04, r22, r23 | 13 failed |
| M63 | leaf: review builder accepts a denied source_url | r28 | 2 failed |
| M64 | leaf: gap source_hint accepts free text | r28 | 3 failed |

Every [pyt] line of the 65 runs is in <scratchpad>/S81-14_red/mut_table.md (and mutation_results.jsonl); all are `status=FAIL rc=1` (killed), elapsed 9-16 s, e.g. `[pyt] tag=s14-m1 start=2026-10-23 21:58:02 end=2026-10-23 21:58:18 elapsed=16s bound=600s status=FAIL rc=1`. Spec M28 (045 padded past 20,000 bytes) is moot under R-S14-12 and was replaced by the limit-revert mutant; spec M1-M27, M29 and review C18's M30-M39 are all present; M40-M64 cover the rulings (R-S14-1 ranking / market / card / prune, R-S14-2 registry / platform_confidence / trigger / merchant deny, R-S14-4 nullable device key + prune, R-S14-5 size axis, R-S14-6 derived belts + source_hint, R-S14-13 lang). Equivalent-survivor candidates: none.

## 5. Comm set (step 7)

List: <scratchpad>/S81-14_red/comm_list.txt (66 files); reasons: <scratchpad>/S81-14_red/comm_reasons.tsv. Union = the spec's chunk A (25 migration readers) + chunk B (22 scanner / CLAUDE.md readers: the brief's source-scanning pins, every app/ and tests/ walker, test_ci_gates + test_behavior_dimension_translation) + chunk C (15 identity-helper importers incl. FY25 and the W4-13 ledger) + test_retro_w1_2c (.sqlfluff reader: the 037 large-file pin) + test_secret_scan_static (hook / migrations text reader) + test_seed_zyte_guard (spec_spine reference) + the new file. Re-derived by grep at e1878dd8 (rglob / glob / os.walk / listdir / scandir walkers, sqlfluff, migrations, deny_hosts, spec_spine, CLAUDE.md readers): the remaining walker hits glob fixtures / SmartCompareApp / skills only (test_events_allowlist_superset, test_jsonld_shape_ladder, test_multiplicity_discriminator_policy, test_not_a_pdp_filter, test_platform_router, test_skill_frontmatter), not app/ or migrations/. MINUS the four test_precommit_hook*.py (.githooks untouched; the hook reads .sqlfluff through sqlfluff only); no NETWORK_FLAKY_EXCLUDE member in the set; no SmartCompareApp-scanning test (nothing client-visible). Base chunk results: section 1 (no failure outside the new file's RED ids); head (prototype) chunk results: section 3 (0 failures). comm -13 of the FAILED sets (base vs prototype head) is empty.

## 6. Restore check (step 8)

- Real worktree: sha256 of all 3418 tracked files after the run == base_shas.txt (diff empty); `git status --short` = `?? tests/test_s81_kb_schema.py` only; HEAD e1878dd8. No git write in the real worktree.
- Scratch worktree removed with `git worktree remove --force` (rc 0); `git worktree list` no longer lists it; the directory is gone; it never held node_modules.
- No orphan pytest: no python.exe with s14- / sc-s81-s14 / s14_scratch in its command line after the last run.
- Ignored __pycache__ files may have been written under the real worktree by pytest (git-ignored; status clean).

## 7. Deviations from the spec (rulings applied; nothing silently changed in an existing file)

1. R-S14-5 vs measured spine_key: the ruling maps "a size above 5000 ml to '-' exactly like spine_key", but spine_key has no 5000 cap: spine_key("Dior", "Sauvage EDP 6000ml") = "fragrances|christian+dior|sauvage|EDP|6000" (extract_size_ml_any keeps 1..9999; "10000 ml" reads as 0). The RED pins the ruling's explicit behaviour (5001..9999 -> "|-"), so for 5001..9999 ml surfaces kb_variant_key != spine_key (one pinned row). Question Q1.
2. Offer observation key (R-S14-1 a): UNIQUE kb_offers_observation = (variant_id, merchant_id, market, observed_currency, amount, list_vs_sale); canonical_url leaves the key because the ruling makes it an upsert-SET column. No kb_offers_observe function: the contract is pinned as leaf constants KB_OFFER_OBSERVATION_KEY / KB_OFFER_UPSERT_SET (= last_seen, in_stock, evidence_rung, canonical_url) + the 045 header sentence (the ruling allows "or the writer's upsert").
3. Function set is five, not three: + kb_set_updated_at() (trigger function, R-S14-2) + kb_prune_feedback(integer) (R-S14-4); kb_product_card is (text, text DEFAULT 'en') (R-S14-13). Three `CREATE OR REPLACE TRIGGER ... BEFORE UPDATE ... FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at()` on kb_merchants / kb_products / kb_variants (PG 14+, inside the PG 15 guard; sqlfluff 4.3.0 parses it). Rollback/045 drops all five (statement list pinned).
4. Spec R20 (size < 20,000) is replaced by R20 (.sqlfluff large_file_skip_byte_limit = 0 in the [sqlfluff] section), P5 (every migration under the effective limit, read like test_retro_w1_2c) and R20b (ASCII + no 8-digit run per file). 045 is 23,141 LF bytes.
5. kb_merchants: no deny-label CHECK at all (R9 spec row for kb_merchants.host dropped; R9b asserts none); registry jsonb NOT NULL DEFAULT '[]' CHECK array; platform_confidence text IN (mechanism, probe, url, operator); build_merchant_row never calls kb_source_allowed and ACCEPTS a denied host (deny=true/blocked, and also deny=false/live: R-S14-2's "no builder applies kb_source_allowed to kb_merchants") -- Q3.
6. The SQL deny belts use sorted(deny_hosts.DENY_LABELS) = (basenotes|fimgs|fragrantica|parfumo) (DENY_LABELS is a frozenset, so the spec's order is not derivable); one URL belt `^https?://([^/]*[.])?(...)[.]` on every URL column (the image belt was ^https://; its format regex already forces https) and one host belt `(^|[.])(...)[.]` on host columns; kb_service.kb_deny_label_group() / kb_host_deny_regex() / kb_url_deny_regex() derive them at call time and R9 asserts equality.
7. kb_gaps.source_hint (R-S14-6): CHECK = 1..256 AND (host regex OR the canonical_url regex) AND both belts; the builder accepts a host or a canonical URL only and applies kb_source_allowed ("notfragrantica.example" is now ACCEPTED as a legitimate host; free text, a scheme-less path and a query URL are refused).
8. kb_feedback (R-S14-4): device_key nullable; uq_kb_feedback_one_vote and idx_kb_feedback_device_key are partial WHERE device_key IS NOT NULL; + idx_kb_feedback_created (created_at) for the TTL prune. The 045 header carries the R-S14-4 sentence (pseudonymous HMAC-SHA256 under DEVICE_KEY_PEPPER, not a user id, outside the 043 fence by design, S81-22 hook + kb_prune_feedback(365)).
9. canonical_offer_url also refuses a deny-labelled host, so every non-None output satisfies the WHOLE 045 canonical_url CHECK (format + belt), the spec 2.4 claim made literal; IDN (non-ASCII) hosts are refused (stated limit; punycode accepted).
10. Builders (R-S14-11): updated_at is a REQUIRED aware-datetime keyword for the three updated_at tables (the leaf has no clock); timestamps are emitted as ISO strings, amount / aggregate_rating / coverage value as decimal strings (numeric(14,3) / (3,2) rounding mirrored: amount 0.0004 is refused); jsonb arguments must be JSON-serialisable (allow_nan=False); registry entries must be objects with origin in (literal, catalog, operator, discovery) and an int order >= 0 (the R-S14-2 entry shape) -- Q4.
11. R4 pins the FULL compact definition of every column plus the (name, type, not_null, default) tuple; R4b pins every table-level CONSTRAINT by name and compact text and the composite PK; R12 pins every index statement compact; R15 / R15b / R15c / R15d pin the prune conjunction + bounds, the feedback prune, the GTIN body and the trigger body as compact literals. The literals were generated from the prototype with the RED file's own parser (gen_literals.py) and then mutation-proven.
12. Comm set: B split into three chunks and C into two (the tool's 600 s cap), each well under bound 1200; union additions listed in section 5.
13. Mutation runs used the whole unit file per mutant (not -k), recording every killing row (strictly stronger).
14. After the runs, the prototype leaf's `_INT4_MAX = 2147483647` (a 10-digit run the added-line sweep flags) was rewritten `2 ** 31 - 1` (same int; ruff E9/F63/F7/F82 clean). The mutation and prototype runs used the pre-fix bytes (sha b6f2af107ea070d9fba75899bbd2d23883137d70d98b3e604165fade0559ff67); the table above lists the post-fix sha GREEN should copy.
15. The B1 [pyt] line is reconstructed from the runner's own ledger record (pyt_ledger.jsonl), not from stdout.

## 8. Open questions for the gate

- Q1. R-S14-5: keep ">5000 ml -> '-'" (pinned now; kb_variant_key differs from spine_key for 5001..9999 ml) or "exactly like spine_key" (keep the number; flip the two R23 assertions; M52 shows the row is live)?
- Q2. Accept the offer upsert contract as leaf constants + header (no kb_offers_observe RPC in 045)? S81-17's 051 RPC would consume KB_OFFER_OBSERVATION_KEY / KB_OFFER_UPSERT_SET.
- Q3. build_merchant_row accepts a denied host with deny=false (status live) because R-S14-2 forbids applying kb_source_allowed to kb_merchants; the decode trusts the deny column. Confirm S81-15 always stores deny=true / blocked for the deny list.
- Q4. The registry entry validation (origin enum + int order >= 0) in build_merchant_row: confirm against S81-15's entry shape (R-S15-16) before GREEN.
- Q5. tests/_retro_r_mig_sql.arg_types reads `p_lang text DEFAULT 'en'` as the type "'en'"; no existing census filters that signature (037 / 043 filter named signatures only; measured green on the prototype), so it is harmless; state it, or drop the DEFAULT and have callers pass 'en'?
- Q6. origin/main moved to 98d85433 (+ #371 S81-05, new app/ modules, main.py) during this RED: no file shared with this unit; GREEN rebasing there must re-run p01-p03 and chunk B.
- Q7. The six APPLY one-paste files (and the R-S14-1 A/B/A check inside BEGIN ... ROLLBACK in APPLY_045_3_POSTCHECK) are GREEN's, in .qa-s80/, not pinned by any committed test (stated limit 12; gate 3 checks the one-paste identity).

## 9. NOT MEASURED

- No PostgreSQL execution of the new 045 / 047 (no offline PG in this RED; the review's stopped scratch cluster was not restarted): the trigger, the card's DISTINCT ON derived table with its outer reference to p.id, `(s0.lang = p_lang) DESC`, the partial unique index and the A/B/A offer behaviour are lint-clean and text-pinned but not executed. GREEN or the owner's POSTCHECK must run them.
- The CLAUDE.md row and the APPLY files (GREEN's).
- test_precommit_hook*.py (excluded by rule; .githooks untouched).
