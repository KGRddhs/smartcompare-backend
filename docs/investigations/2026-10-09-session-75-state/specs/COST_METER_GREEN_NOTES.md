# COST-METER GREEN agent notes (session 75, 2026-10-09)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-s74-u13e, branch feature/s75-cost-meter, HEAD 4c0f3c99.
Budget 2 h from the first tool call.

## Step 0: RED hashes re-verified (match)
- tests/test_cost_meter_s74.py f2985b3143a2d01ed5309ece0f55a406f3507464b3e9a6e071fe005fe9324110 OK
- tests/test_cost_dashboard.py e71f5c379973d6541e7a929d40bda4142cd20f399b1ac3bb3fa29828e8249a90 OK
- git status: M tests/test_cost_dashboard.py, ?? tests/test_cost_meter_s74.py; no .qa-mutation.lock.
- Every touched backend file is i/lf w/crlf (git ls-files --eol): admin_routes, image_routes, share_routes,
  api_budget_service, response_builder, SCS, costs.html, db_offload, test_admin_referral_endpoints,
  test_cost_dashboard, CLAUDE.md, APP_STORE_LAUNCH_RUNBOOK.md, READINESS_BACKEND.md.

## Plan
1. Write cm15b (G5) and cm17 (G9 M7) into tests/test_cost_meter_s74.py FIRST; run them RED on current bytes.
2. New leaf app/services/openai_pricing.py (LF, ASCII, stdlib only) incl. merge_openai_summaries.
3. Chokepoint, builder, SCS (init + two entries + three build sites), admin_routes (_openai_rows/_aggregate_openai,
   api_costs, costs_api), image_routes merge, share strip, costs.html.
4. G2 amendment (test_admin_referral_endpoints.py) shown RED after the rename, then GREEN.
5. G3 netguard stub for cm13/cm14 (patch the Shopify catalog fetcher), ratchet exit 0.
6. G8 gates in order, G9 mutants under the lock, G10 hygiene, G11 docs.

## Measurements
- RED-first (before any production change), cm15b + cm17 added to tests/test_cost_meter_s74.py:
  [pyt] tag=cm-red-first-15b-17 start=2026-10-09 17:29:32 end=2026-10-09 17:29:35 elapsed=4s bound=600s status=FAIL rc=1
  cm15b: AssertionError calls 2 != 3 (the route passes the compare's metadata.openai through unmerged = the
  "overwrite with the compare summary" shape); cm17: ModuleNotFoundError app.services.openai_pricing.
- Production edits done (leaf, chokepoint both branches, builder kwarg, SCS init + 2 entries + 3 build sites,
  admin_routes helpers + both endpoints, image_routes merge, share strip, costs.html). py_compile + ruff clean.
  git diff --stat == git diff --stat --ignore-cr-at-eol (8 files, 365+/80-). No added non-ASCII line after
  replacing the carried em dash (admin_routes docstring) and the bullet (costs.html meta line) with ASCII.
- G8 (1) pins: [pyt] tag=cm-g8-1-pins start=2026-10-09 17:34:44 end=2026-10-09 17:34:52 elapsed=8s bound=600s status=OK rc=0 ; 110 passed (= baseline).
- G8 (2) BEFORE the G2 amendment: [pyt] tag=cm-g8-2-unit-pre-g2 start=2026-10-09 17:35:21 end=2026-10-09 17:35:26 elapsed=5s bound=600s status=FAIL rc=1
  1 failed (the G2 node, openai_paid_usd gone), 54 passed (all 23 cm nodes incl. cm15b/cm17 + the amended dashboard nodes).
  netguard: the Shopify products.json egress is gone (the _no_egress stub); 12 attempts remain from cm13/cm14 to
  9KHJLG93J1-dsn.algolia.net (Algolia tier-2) -> stub next.
- G2 amendment applied (tests/test_admin_referral_endpoints.py, 43+/13-, CRLF kept, no non-ASCII added).
- _no_egress() final shape: price_service._fetch_shopify_catalog -> None; algolia_service._algolia_query -> [];
  _algolia_query_explicit -> None; curl_cffi.requests.Session.request / AsyncSession.request -> RequestsError
  (the backstop: the next rung was search.unbxd.io, then the rest of the adapter ladder).
- G8 (2) AFTER G2: [pyt] tag=cm-g8-2-unit-b start=2026-10-09 17:38:56 end=2026-10-09 17:39:00 elapsed=4s bound=600s status=OK rc=0 ; 55 passed
  netguard blocked 0 attempts from 0 nodes; ratchet: [netguard-ratchet] OK: 0 attempting node(s), baseline 205 ; rc=0 (NO baseline change).
- Base scratch worktree: <notes>/base at 4c0f3c99 (detached, no node_modules, no .env).
- Comm set: 155 files reference the G8 patterns; 4 non-test modules dropped (tests/_env_safety.py, tests/conftest.py,
  tests/fixtures/_gen_w4_13_flag_off_ledger.py, tests/w4_11_prompt_digest_recorder.py) -> 151 test files, CI order;
  first 120 run in chunks 25/25/25/25/20, 31 NOT MEASURED (not_measured.txt).
- chunk 0: HEAD [pyt] tag=cm-comm-00-head ... elapsed=62s status=FAIL rc=1 (3 failed, 1570 passed) ;
  BASE [pyt] tag=cm-comm-00-base ... elapsed=63s status=FAIL rc=1 (3 failed, 1567 passed) ; branch-only-NEW []
  (the 3 = tests/test_camera_vision.py::TestIdentifyProductsMocked x3, pre_impl baseline).
- chunk 1: HEAD [pyt] tag=cm-comm-01-head ... elapsed=31s status=OK rc=0 (537 passed) ; BASE ... elapsed=30s status=OK (514 passed, cm file absent) ; NEW [].
- gitleaks dir over copies of the 14 changed files, repo .gitleaks.toml: no leaks found, rc=0.
- chunk 2: HEAD [pyt] tag=cm-comm-02-head ... elapsed=35s status=FAIL rc=1 (2 failed, 395 passed) ; BASE ... elapsed=36s status=FAIL (2 failed, 395 passed) ; NEW []
  (the 2 = tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities,
  ::test_full_response_payload_audit_no_magnitude_keys, both in tests/.pre_impl_failures.txt territory / identical at base).
- chunk 3 FIRST RUN: HEAD [pyt] tag=cm-comm-03-head ... elapsed=89s status=FAIL rc=1 (6 failed, 979 passed) ; BASE ... elapsed=89s status=OK (985 passed) ;
  branch-only-NEW = 6 camera body pins in tests/test_retro_w2_1.py (W2-1): they stub identify_products (0 dispatches) and fake the
  compare (no openai key), and my route attached a calls-0 vision summary -> `metadata.openai` extra key broke the byte-identical
  body pins. FIX (production side, zero effect in prod where identify_products always dispatches): attach metadata.openai only when
  the compare returned its own summary or the vision ledger recorded >= 1 call. Re-run of the file + the cm nodes follows.
- W2-1 recheck after the camera guard: [pyt] tag=cm-w21-recheck start=2026-10-09 17:51:04 end=2026-10-09 17:51:08 elapsed=5s bound=600s status=OK rc=0 ; 134 passed
  (tests/test_retro_w2_1.py + tests/test_cost_meter_s74.py), netguard 0.
- chunk 4: HEAD [pyt] tag=cm-comm-04-head ... elapsed=55s status=OK rc=0 (768 passed) ; BASE ... elapsed=56s status=OK (768 passed) ; NEW [].
- chunk 3 head rerun attempt 1: rc=4 in 0 s = a pytest USAGE error (the chunk file is CRLF on Windows and `tr '\n' ' '` left a CR in
  every path) -> not a result; rerun with `tr -d '\r'` first.
- The shared comm failures (camera_vision x3 chunk 0, personalization_bundle_c x2 chunk 2) are rows of tests/.pre_impl_failures.txt (11 rows).
- chunk 3 head RERUN after the camera guard: [pyt] tag=cm-comm-03-head-rerun start=2026-10-09 17:53:45 end=2026-10-09 17:55:12 elapsed=87s bound=1200s status=OK rc=0
  (985 passed, 2 skipped, 1 deselected) == BASE 985 passed -> NEW [].
- Mutants (mutants.py, byte copy -> mutate -> killing node(s) via pyt.py bound 600 -> restore -> sha256 equal; lock held
  17:55:13-17:56:05 then removed): M1-M12, M14 all KILLED, restore sha256 ok each (table in the report). M13a/M13b patterns
  were stale after the camera guard edit (x0, not applied) -> patterns updated, rerun separately.
- Base worktree removed with git worktree remove --force (git worktree list shows none).
- M13a / M13b (patterns fixed): both KILLED by cm15b, restore sha256 ok; lock removed 17:57:18.
- gitleaks dir over fresh copies of all 14 changed files (after every edit): no leaks found, rc=0.
- FINAL: [pyt] tag=cm-final-unit-and-pins start=2026-10-09 17:57:45 end=2026-10-09 17:57:56 elapsed=10s bound=600s status=OK rc=0 ; 165 passed
  (pins 110 + unit files 55) on the restored final bytes. final_sha.py output = the files_changed list of the report.
- Comm NOT MEASURED (31, CI order, by name): see not_measured.txt (tests/test_specs_no_fabrication_guard.py ... tests/test_youtube_flag_and_cache.py);
  tests/test_u3c_store_false_pin.py among them is covered by gate (1) and the final run.
- Closed 2026-10-09 ~17:58 local (about 65 min of the 2 h budget).
- Docs edits: CLAUDE.md +1 line (end of the SESSION 73 block), runbook row 35 and READINESS_BACKEND RB-35 (1 line each); CRLF kept, ASCII.
