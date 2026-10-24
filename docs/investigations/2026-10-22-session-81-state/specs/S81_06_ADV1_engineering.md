# S81-06 ANTHROPIC-ROUTER: adversary (engineering lens) report

Agent: adversary, lens engineering, Opus 5.5. Unit S81-06 (lane A). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s06, branch feature/s81-s06-anthropic-router, HEAD ceecb04a1a4c9e58c62eebe07705148a979eb31e (verified at start and end; git status --short empty both times). Base ea3aef15.
Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/S81-06_adv/ (every file of this lens is prefixed eng_: eng_notes.md, eng_pyt.py, eng_derive.py, eng_mine_reasons.txt, eng_missing_main.txt, eng_chunk_*.txt, eng_mut.py, eng_mutants.json, eng_mut/, every *.log). Written through the shell.

VERDICT: NOT_READY (0 BLOCKING, 2 MAJOR on the comm-set gate, 7 MINOR).

## Setup
- Dedicated venv C:/Users/SynAckITPC/Documents/AI/.venv-s81-06/Scripts/python.exe: anthropic 1.12.1, Python 3.12.9 (measured). The shared pyt.py hard-codes VENV_PY=.venv-qaren (line 30) and spawns [VENV_PY, "-m", "pytest"] (line 87), not sys.executable, and documents no interpreter option; every run used the copy eng_pyt.py (two lines changed: HERE = the shared harness dir, VENV_PY = the dedicated venv; the shared pyt.py untouched). Same as GREEN D1.
- Scratch worktree: `git -c core.longpaths=true worktree add --detach <scratchpad>/S81-06_adv_engineering ceecb04a` (removed at the end with `git worktree remove --force`, then `git worktree list` checked). No node_modules junction. Mutation lock <scratch>/.qa-mutation.lock created by eng_mut.py and removed after each batch; every restore sha-verified (OK x7).
- RED file sha256 8e1e03e66eac67ffc0849a0b01094c835467d0d11127834df2b7aba368bae84b: the committed blob (`git show HEAD:...`) and the worktree file, at the start and at the end.
- Box: slow (a plain `ls` 2.1 s; the unit file set took 140 s here vs 28 s for the correctness adversary two hours earlier); no pytest of another session ran during my runs (only the stall monitor).

## Runs ([pyt] lines; HEAD bytes in the scratch worktree; dedicated venv)
- unit files (both): `[pyt] tag=s06adv-e-unit start=2026-10-24 14:08:36 end=2026-10-24 14:10:56 elapsed=140s bound=600s status=OK rc=0` 374 passed; `[hermeticity] sentinel checked 374 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`
- MISSING app.main importers chunk m1 (25 of the 27 files GREEN's set lacks, MAJ-E1): `[pyt] tag=s06adv-e-m1-head start=2026-10-24 14:13:47 end=2026-10-24 14:14:28 elapsed=41s bound=1200s status=FAIL rc=1` 2 failed, 472 passed, 1 deselected; the 2 = tests/test_auth_interceptor.py::test_sign_in_with_social_exception and ::test_social_login_user_insert_fails_gracefully, both rows of tests/.pre_impl_failures.txt (accepted baseline, AssertionError on the [B4-BE-DIAG] message); `[hermeticity] sentinel checked 474 test(s)`; `[netguard] blocked 90 attempt(s) from 13 node(s)`
- pins + readers chunk p (23 files: test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_sentry_channels_u8d (SR8), the CLAUDE.md readers test_ci_gates + test_behavior_dimension_translation, the legal / manifest readers test_legal_docs_u8, _d3c, _polish, test_legal_disclosure_s77, test_legal_s78 (R22), test_legal_routes, FY25 test_s75_fanout_identity, W4-13 test_w4_13_flag_off_ledger, test_s81_s05_request_context (E9), test_s81_s04_spend_breaker (K1), test_retro_w1_3, test_be_harness; + the last 2 missing app.main importers test_url_validator_offloop, test_version_routes): `[pyt] tag=s06adv-e-p-head start=2026-10-24 14:15:53 end=2026-10-24 14:17:51 elapsed=117s bound=1200s status=OK rc=0` 1522 passed; `[hermeticity] sentinel checked 1522 test(s)`; `[netguard] blocked 44 attempt(s) from 3 node(s)`
- CI-order set of my own (25 files sorted: the two unit files FIRST, then 23 later-alphabet comm files at leak risk: test_security_regression, test_sentry_503_suppression, test_sentry_channels_u8d_unit, test_sentry_service, test_shutdown_drain, test_streaming, test_structured_comparison_service, test_text_error_envelope_no_raw_exception, test_text_routes_error_mapping, test_text_routes_sse_contract, test_two_input_shape, test_u13e_url_detect_guard, test_u3b_sharing_branch_removed, test_u3c_store_false_pin, test_url_compare_category, test_url_extraction, test_variant_llm_hint_b3b, test_verdict_critique_service, test_version_routes, test_w49_extraction_catch_redaction, test_w4_12_display_contract, test_w4_13_measurement_truth, test_wall_caps_i57): `[pyt] tag=s06adv-e-ciorder start=2026-10-24 14:19:32 end=2026-10-24 14:21:49 elapsed=137s bound=1200s status=OK rc=0` 1306 passed, 2 deselected; `[hermeticity] sentinel checked 1306 test(s)`; `[netguard] blocked 139 attempt(s) from 65 node(s)`
- GREEN comm chunk 09 (test_openai_breaker et al.): `[pyt] tag=s06adv-e-c09-head start=2026-10-24 14:26:11 end=2026-10-24 14:27:02 elapsed=51s bound=1200s status=FAIL rc=1` 2 failed (the two accepted test_page_scraping nodes), 3639 passed, 22 skipped = GREEN's s06g-comm-head-09 exactly; `[hermeticity] sentinel checked 3642 test(s)`; `[netguard] blocked 130 attempt(s) from 9 node(s)`
- GREEN comm chunk 12 (test_retro_w1_3, test_retro_w1_7_w1_10 /health): `[pyt] tag=s06adv-e-c12-head start=2026-10-24 14:27:31 end=2026-10-24 14:29:28 elapsed=117s bound=1200s status=OK rc=0` 884 passed = GREEN; `[hermeticity] sentinel checked 884 test(s)`; `[netguard] blocked 20 attempt(s) from 1 node(s)`
- GREEN comm chunk 05 (test_health_brand_s69, test_health_loop_lag): `[pyt] tag=s06adv-e-c05-head start=2026-10-24 14:29:36 end=2026-10-24 14:33:54 elapsed=259s bound=1200s status=OK rc=0` 1947 passed, 1 skipped = GREEN; `[hermeticity] sentinel checked 1948 test(s)`; `[netguard] blocked 63 attempt(s) from 40 node(s)`
- the four pre-commit hook files, one call: `[pyt] tag=s06adv-e-hooks start=2026-10-24 14:46:30 end=2026-10-24 15:06:39 elapsed=1209s bound=1200s status=TIMEOUT rc=124` (progress `....F.FFF....F` before the kill, no failure report printed). NOT MEASURED: the one permitted re-run did not fit the 90 min budget. The unit edits none of the files the hook tests read (.githooks/pre-commit, the hook test files, pyproject.toml, .gitleaks.toml are byte-unchanged in `git diff ea3aef15 HEAD`; the scenarios build their own tmp repo with a one-entry black allowlist, tests/test_precommit_hook.py:241), so the F marks are not attributable to these bytes without a base run in the same venv (black 26.5.1 and gitleaks present).
- Mutants: 7 runs below, each `[pyt] tag=s06adv-e-mut-<id>` bound 600 (lines in eng_mut/<id>.log).

## Diff hygiene (git diff ea3aef15 HEAD, 35 files, numstat = the GREEN report's +/- table exactly)
- Blobs: every changed blob is LF (0 CR bytes, measured per blob with git cat-file); the high-byte count of every changed file is identical base vs head (CLAUDE.md 3937 / 3937: the two edited Environment Variables lines keep their pre-existing em dashes; every added line is pure ASCII). The scratch working copy is CRLF everywhere (autocrlf), no whole-file diff.
- No deleted line without a reason: the 2-to-30 line modifications are the 16 dispatch rewrites (`guarded_llm_create(` -> `_llm_router.route("<site>", _llm_breaker.guarded_llm_create,`), the six flag-gated except-arm wraps (the base line is kept verbatim in the else arm), the timeout reads, the cost readers, the deliberate pin edits E1-E10 / GC-7a-c.
- New imports: `from app.services import llm_router as _llm_router` in extraction_service, openai_service, image_service, url_extraction_service, verdict_critique_service, structured_comparison_service, image_routes, url_routes (+ `LLM_UNAVAILABLE_FRIENDLY_MESSAGE` in url_routes) and LAZY imports in cache_service.get_comparison_cache_key (the router -> api_budget_service -> cache_service cycle) and content_safety_service.moderate_output; llm_router itself imports api_budget_service, llm_pricing, llm_spend_breaker, model_config, request_context at top and the SDK only through importlib at call time; sentry_service imports anthropic + sentry_sdk.integrations.anthropic inside init_sentry's guarded try. All within the spec's change list as I read it; no package import outside requirements.in.
- ruff 0.16.5 `--select E9,F63,F7,F82` on all 26 changed .py: clean; py_compile clean; json.load of processors.json and both fixtures: OK. Extended (non-gating) F401/F811/F841: one NEW finding in production bytes (m3) and 18 F811 in the gate-rows file (imported pytest fixtures shadowed by parameters, the pytest idiom; noise).
- requirements.in: `anthropic==1.12.1` with the orchestrator note; the lock is NOT recompiled on these bytes, so CI's Lock-is-current step fails until the orchestrator does it (known, stated). Measured: anthropic 1.12.1 requires anyio, docstring-parser, httpx2, jiter, pydantic, sniffio, typing-extensions; requirements.txt already pins httpx2==2.12.0 and jiter==0.16.0 and has no docstring-parser, so the PR body's "anthropic==1.12.1 + docstring-parser" is consistent with the lock (resolver output not measured: no uv).

## Comm set (union rule re-derived at HEAD: eng_derive.py)
Classes grepped over tests/: module names of the 13 edited app modules + fill_in_legal; app.main (`app.main`, `from app import main`, `app/main.py`, `health_check`, `"/health"`); 27 edited / routed symbols; the edited helpers (_env_safety, w4_11_prompt_digest_recorder, legal_fill_in_u8, legal_s78); source scanners (inspect.getsource, ast.parse, glob / rglob, listdir / scandir / walk, __file__, "app" segments, "app/" strings, .github, CLAUDE.md, processors.json / app/legal, requirements.*, black-clean-paths, SmartCompareApp, railway.json / Procfile, migrations); minus test_precommit_hook*.
Result vs GREEN's 461 (= the gate's 447 UNION 14; gate-not-in-GREEN EMPTY): every source-scanning, helper, legal, CLAUDE.md, client-scan and module-name member is in GREEN's set (the only scan-class extras are 4 migrations readers, not members: no migration changed). MISSING: the 27 importers of the edited app.main whose only reference is app.main (MAJ-E1). The two unit files are outside by design.

## Findings

### MAJOR
- MAJ-E1 (common brief comm rule, module reference of an EDITED module; "a missing file is a MAJOR"): app/main.py is edited (the additive `anthropic_breaker` /health snapshot, app/main.py:349-354 and :648) and `import app.main` now transitively imports llm_router through eight modules, yet the comm set (the gate's 447 and GREEN's 461) holds only the 77 app.main importers that ALSO name another edited module; 27 of the 106 app.main importers are absent:
  tests/test_account_deletion_u8b_fix_pins.py
  tests/test_auth_interceptor.py
  tests/test_auth_preference_toggles_w314.py
  tests/test_cost_dashboard.py
  tests/test_endpoint_shapes_vs_jsx.py
  tests/test_feedback.py
  tests/test_history_routes.py
  tests/test_home_routes.py
  tests/test_invitee_quiz.py
  tests/test_m13_01_slowapi_middleware.py
  tests/test_m13_21_openapi_gated.py
  tests/test_m13_28_referral_hardening.py
  tests/test_m13_29_feedback_uuid.py
  tests/test_profile_routes.py
  tests/test_push_token_endpoint.py
  tests/test_rate_limiting_complete.py
  tests/test_referral_feature_flag.py
  tests/test_referral_must_fixes.py
  tests/test_referral_routes.py
  tests/test_referral_share_privacy.py
  tests/test_s80_b1_feedback.py
  tests/test_share_routes.py
  tests/test_social_login_device_fingerprint.py
  tests/test_social_login_smoke.py
  tests/test_supabase_client_reuse.py
  tests/test_url_validator_offloop.py
  tests/test_version_routes.py
  Measured at HEAD (above): 2 failed (the accepted test_auth_interceptor pair of tests/.pre_impl_failures.txt) / 472 passed + the 2 in chunk p green, so no regression was found, but the zero-regression gate as recorded does not cover them and there is no base record for them. Fix: add the 27 files (two chunks) to the comm record, base and head.
- MAJ-E2 (GC-9; concurs with the correctness lens MAJ-3, GREEN D12): GC-9 requires the comm set "HEAD vs a base record at the GREEN base ... branch-only-new EMPTY". GREEN ran HEAD only (19 chunks) and the PR body still states "branch-only-new = EMPTY against the accepted baselines": that is "HEAD failures a subset of the accepted baselines", not a `comm -13` against base. My three re-run chunks (05, 09, 12) reproduce GREEN's HEAD counts exactly, but I ran no base record either (budget). Fix: the base record at ea3aef15 for all chunks (incl. the MAJ-E1 files), then rewrite the PR body line.

### MINOR (documentation / follow-up rulings)
- m1 (E4 pin strength, mutant MPA SURVIVED): the Anthropic half of tests/test_u3c_store_false_pin.py::test_u3c_02 flags only `.create/.stream/.parse/.count_tokens` whose receiver is an attribute named `messages` (or messages.batches); an aliased Messages object escapes: `msgs = client.messages; await msgs.create(model="m", max_tokens=1, messages=[])` added to app/services/image_service.py left the file green (`[pyt] tag=s06adv-e-mut-MPA_alias_bypass start=2026-10-24 14:37:22 end=2026-10-24 14:37:29 elapsed=7s bound=600s status=OK rc=0`). The OpenAI twin flags the `chat.completions` chain itself, plus REST paths and getattr names; the Anthropic rule has no REST-path ("/v1/messages") or getattr("messages") arm. (`with_raw_response` is caught by the OpenAI SDK_WRAPPERS arm regardless of provider.) Suggest a follow-up bypass shape for the alias and the REST path.
- m2 (E1 / E3 census pins do not enforce routing, mutant MPC SURVIVED / MPC2 KILLED): un-routing image_tier3 back to a direct `_llm_breaker.guarded_llm_create(` keeps test_model_config_enforced and test_u3c_03 green (they count routed AND direct calls; the base already had 16 direct `guarded_llm_create(` calls by grep count: extraction x8, openai_service x5, image, url_extraction, critique, measured with git show ea3aef15; the census itself was not run at base), `[pyt] tag=s06adv-e-mut-MPC_unrouted_site start=2026-10-24 14:37:31 end=2026-10-24 14:37:54 elapsed=22s bound=600s status=OK rc=0`; the routing is enforced only by the unit file's R04 (`[pyt] tag=s06adv-e-mut-MPC2_unrouted_site_unit start=2026-10-24 14:39:22 end=2026-10-24 14:39:48 elapsed=26s bound=600s status=FAIL rc=1` KILLED). The PR body E1/E3 reason "the 16 sites call the router" reads as if the census enforced it; the floor 15 -> 16 is no tighter than the base census (16 at base). Wording ruling.
- m3 (stale import): app/services/structured_comparison_service.py still imports `openai_preflight_allows_compare` (the import block at :72-74 and its comment "the READ-ONLY half deliberately") although `_llm_preflight_short_circuits` now calls `_llm_router.active_provider_preflight_allows()`; ruff F401 on that module: 15 findings at base, 16 at HEAD (the new one is this name). No test patches the scs-level name (grep), so nothing went vacuous; cosmetic.
- m4 (Sentry SR8 sequencing, R-S06-13): tests/test_sentry_channels_u8d.py BASE_INTEGRATIONS now lists AnthropicIntegration unconditionally (the present state; the absent state is pinned by R34b in the unit file), so in any venv without the SDK (the shared .venv-qaren until the orchestrator syncs it, and CI until the locks are recompiled) the SR8 node is red. The orchestrator's merge window must recompile the locks AND update .venv-qaren together, or sibling lanes' SR8 reddens; and with the SDK installed the explicit AnthropicIntegration is active in production unflagged (include_prompts False; no Claude call is made with every role flag OFF).
- m5 (PR body / row truth): the PR body's comm-set paragraph omits the app.main importer class (MAJ-E1) and its "branch-only-new = EMPTY" line has no base record (MAJ-E2); the CLAUDE.md row cites "(R-S03-9)" for "ENABLE_LLM_SPEND_BREAKER ON before ENABLE_ANTHROPIC_VERDICT" where GC-11 states the precondition as "S81-04 ON before VERDICT" (the R-S03-9 text was not read here: NOT VERIFIED). Every other row claim I checked matches the bytes: the 16 sites and their split (extraction x8, openai_service x5, image_service, url_extraction_service, verdict_critique_service), the knob defaults (2 / 25.0 / 4.0 / 20.0 / 6.5, the _float_knob rule), the model defaults (claude-haiku-5-5 x5, claude-sonnet-5-5), the three CREDENTIALS_UNSET names, the four WARNING-by-type log sites (parse, generate_comparison, image_routes vision exit, url extract), the cache axis only when decide("verdict") == "anthropic", the /health key only after the `ran` latch, the 5,000,000-byte cap and 2,576 px edge, the camera strings at SmartCompareApp/app.json:220 and :228 naming OpenAI, the U3c 01/01b/01c and K1 pins untouched (api_budget_service.py is not in the diff), the anchor order B1, B3, B4, D03, S81-03, ST1, S81-05, S81-04, S81-06 (CLAUDE.md:474-497), the Environment Variables Optional + Feature Flags lines.
- m6 (style): the processors.json anthropic row stores category_ar as \u escapes while every other row stores raw UTF-8 Arabic (json-equivalent; R22 / R36 / T7 green); keep or normalise in S81-12's rebase of the same row.
- m7 (pre-existing doc drift, not this unit): CLAUDE.md's W4-11 and SESSION 65 sentences say "all 15 LLM call sites" / "15 measured call sites" / "an AST pin over >= 15 sites"; the base census was already 16 and the floor is now 16 (R-A15: rewrite in place in a docs pass).

## Pin-strength mutants (scratch worktree, byte copy -> exact edit matching once -> py_compile -> the killing pin -x -> restore -> sha256)
- MPA alias Messages bypass in image_service (u3c_02): SURVIVED (m1).
- MPC un-route image_tier3 (enforced census + u3c_03): SURVIVED (m2, by design of the census); MPC2 same edit vs the unit file -k r04: KILLED (`...MPC2_unrouted_site_unit ... status=FAIL rc=1`).
- MPD an AsyncAnthropic constructor with api.anthropic.com in image_service (E6 / T7b): KILLED by tests/test_legal_docs_u8.py::test_t7b_external_hosts_and_clients_map_to_manifest (`[pyt] tag=s06adv-e-mut-MPD_client_elsewhere start=2026-10-24 14:39:52 end=2026-10-24 14:40:05 elapsed=13s bound=600s status=FAIL rc=1`).
- MPE drop the eighth flag from scripts/fill_in_legal.py SEVEN_FLAGS (GC-7a): red by the script's own FillInError in tests/test_legal_docs_u8.py::test_fix_b1_fill_in_rerun_with_the_same_data_changes_nothing (an exception, not an AssertionError; counts as caught) (`[pyt] tag=s06adv-e-mut-MPE_seven_flags_script start=2026-10-24 14:40:09 end=2026-10-24 14:40:34 elapsed=25s bound=600s status=FAIL rc=1`).
- MPF gate_flag null on the anthropic processors row (GC-7c / R22): KILLED by tests/test_legal_s78.py::test_s78_r22_manif... (`[pyt] tag=s06adv-e-mut-MPF_row_gate_null start=2026-10-24 14:40:35 end=2026-10-24 14:41:00 elapsed=24s bound=600s status=FAIL rc=1`).
- MPG a "claude-haiku-5-5" literal in llm_router.py (E5): KILLED by tests/test_model_config.py::TestNoStrayModelLiterals (`[pyt] tag=s06adv-e-mut-MPG_claude_literal start=2026-10-24 14:37:58 end=2026-10-24 14:38:10 elapsed=11s bound=600s status=FAIL rc=1`).
Restores: 7 / 7 OK (sha256 equal); lock created and removed by the harness.

## Prove-nothing rows (engineering view)
- tests/test_s81_s06_anthropic_router.py::test_r37_requirements_pin reads requirements.in only; it proves nothing about the locks or what CI / Railway installs (the real-SDK rows R16 / R34a carry that, in the dedicated venv only).
- test_p09_netguard_blocks_anthropic_host pins `_netguard.classify_host` with no egress attempt (accepted by GC-7); the R-S06-7 "blocked-host list gains api.anthropic.com" is satisfied by classification, tests/_netguard.py is unchanged.
- tests/test_model_config_enforced.py M1 and test_u3c_03 floors 16: no tighter than the base census of 16 direct sites (m2).

## Deviations (mine)
- D-E1 the pinned harness pyt.py cannot take the dedicated interpreter; a two-line copy eng_pyt.py was used (shared ledger and netguard dir).
- D-E2 no base record run (budget); the hook-file gate TIMEOUT not re-run (budget): NOT MEASURED.
- D-E3 the CI-order set is my own 25-file selection (the unit files first, then later-alphabet files at leak risk), not GREEN's 24-file list.

## NOT MEASURED
- The four test_precommit_hook*.py files (TIMEOUT once, see Runs).
- Any base record at ea3aef15 (MAJ-E2).
- The lock recompile / pip-audit of anthropic==1.12.1 (orchestrator-only) and the release-date claim (published 2026-10-08; no network).

## git status --short of the unit worktree
(empty at the start and at the end; HEAD ceecb04a1a4c9e58c62eebe07705148a979eb31e; RED sha 8e1e03e6... unchanged)
