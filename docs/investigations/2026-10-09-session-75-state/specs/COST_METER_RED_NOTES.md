# COST-METER RED agent notes (session 75, 2026-10-09)

Start: 2026-10-09T13:46:47Z (first tool call). Budget 2 h -> hard stop 15:46 UTC.
Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s74-u13e, branch feature/s75-cost-meter, HEAD 4c0f3c99, porcelain clean, hooksPath .githooks.

## Anchor diff (step 1)
`git diff --stat 49883e84 HEAD -- app tests migrations`:
 app/api/admin_routes.py                     |    5 +-
 app/api/url_routes.py                       |    8 +-
 app/main.py                                 |    3 +-
 tests/test_be_harness.py                    | 1833 +++++++++++++++++++++++++++
 tests/test_s71_u13_compare_auth_required.py |   17 +-
 tests/test_s71_u13_harness_auth.py          |    3 +-
 tests/test_u13e_url_detect_guard.py         |  653 ++++++++++
 7 files changed, 2508 insertions(+), 14 deletions(-)
Non-empty: admin_routes.py moved (5 lines). api_budget_service, response_builder, SCS, image_routes, openai_service, share route: NOT in the diff -> spec line numbers hold at HEAD for those; re-verify by grep anyway.

## Decisions log
- (pending) new test file name; CM3 amendments; RED-A; pins baseline.

## Re-anchors (admin_routes.py shifted +3 after :51, the #304 verify_admin_key strip; nothing else in app/ moved)
- api_costs :119-152 -> :122-155; get_supabase_client reads :128/:140 -> :131/:143; `.select("metadata")` :130 -> :133
- costs_api :736-772 -> :739-775; `.limit(2000)` :755 -> :758; output block :789-800 -> :792-803 (openai_paid_usd :794)
- costs_gauges :857-901 -> :860-904
- guarded_llm_create :952-1025 UNCHANGED (verified: def :952, flag-OFF dispatch :978, flag-ON dispatch :985, return :1025)
- response_builder.build_comparison_response :1451 UNCHANGED; metadata block total_cost :2065; override merge :2117-2118
- SCS: __init__ :3090/3091, resets :3727 (impl) / :4292 (streaming), build sites :3529/:4164/:4987, _build_partial_response :3447, complete yield :5101 UNCHANGED
- image_routes: identify_products :299, SCS() :438, compare :439, metadata inject :459-470 UNCHANGED; openai_service.identify_products :141, dispatch :217 (module-level `client` :34)
- share route: app/api/share_routes.py view_shared_comparison :52-72 (passes full_response through untouched)

## Measurements (pinned venv 3.12.9)
- 4o 1000/200/400 -> 0.004 exact; mini -> 0.00024; clamp 100/0/400 -> 0.0005; CM8 1000/200/None -> 0.0045
- cm08 sum 0.0052; avg 0.001733; est 30.01 (F1 trap confirmed: round(30.005,2)=30.0)
- amended node: 0.00424 / avg 0.00212; cm10 10000x0.001 -> 10.0; dedupe 1002 -> 1.002; vision 500/100 mini -> 0.000135

## Decisions
- New file tests/test_cost_meter_s74.py (spec 4.1 names only the class TestCostMeterS74; the task wants a NEW file + the 3 CM3 amendments). Lazy import of openai_pricing per node so cm08-cm12 fail on the pinned defect, not on collection.
- tests/test_admin_referral_endpoints.py::TestCostsApi::test_returns_openai_total_and_daily_burn (spec 4.2) is OUTSIDE my write permission -> flagged for the orchestrator (goes RED under GREEN's CM12 rename).
- cm03 asserts the five spec keys by value + len==1 (not dict equality) so a served_model extra key (review F7 suggestion) is not forbidden.
- cm13/cm14 reuse tests.test_openai_breaker harness (_FanOutCounters/_all/_run_compare/_run_stream) with a usage-bearing fake client; models pinned to defaults via OPENAI_MODEL_* env.
- Limiter disabled in admin/camera nodes (30/min on /costs would 429 across files).

## Files written
- tests/test_cost_meter_s74.py (NEW, 1082 lines, pure ASCII, LF, 21 nodes cm01-cm16 incl. cm05b, cm10b-e): byte-check 0 non-ASCII, 0 CR; py_compile ok; ruff E9,F63,F7,F82 clean; gitleaks dir rc=0.
- tests/test_cost_dashboard.py: 3 CM3 amendments via amend_cost_dashboard.py (byte-exact, snapshot sha 8db37e1e... first); result CRLF-only (git ls-files --eol i/lf w/crlf), 45+/21- (no whole-file diff); the base file already carries one non-ASCII byte (em dash :20) - amendment added none; gitleaks dir rc=0.

## RED-A (base 4c0f3c99)
[pyt] tag=cm-red-a start=2026-10-09 17:10:34 end=2026-10-09 17:10:42 elapsed=8s bound=600s status=FAIL rc=1
24 failed (21 cm + 3 amended), 10 passed (the untouched dashboard nodes). Reasons:
- cm01, cm02, cm03, cm04, cm05, cm05b, cm06: ModuleNotFoundError: No module named 'app.services.openai_pricing'
- cm07: TypeError: build_comparison_response() got an unexpected keyword argument 'openai_usage'
- cm08: AssertionError: cost_usd 0.0 != 0.0052 ; cm09: legacy-only rows must read null, got 0.0 (assert 0.0 is None)
- cm10: range args [] != [(0,999)...(9000,9999)] ; cm10b: [] != [(0,999),(1000,1999)] ; cm10c: KeyError 'rows' ; cm10d: blob fallback did not run: 0.0 ; cm10e: KeyError 'rows'
- cm11: openai_list_usd missing; keys=[avg_cost_per_request_usd, comparisons_with_cost, daily_burn, openai_paid_usd, scrapers, window_days]
- cm12: costs.html must read openai_list_usd (CM12)
- cm13: compare_from_text: metadata.openai absent after 11 dispatches (the compare REACHED a build: success True, metadata present) ; cm14 same on the streaming complete event (11 dispatches)
- cm15: camera identify call not recorded (CM9); metadata keys=[identified_products, input_method, query, total_cost, vision_cost]; vision_cost 0.000135 proves the fake vision dispatch ran through the real identify_products
- cm16: the public share view leaks metadata.openai: ['openai', 'query', 'total_cost']
- amended: test_zero_comparisons_avg_cost assert 0 is None ; test_supabase_error_graceful assert 0.0 is None ; test_openai_cost_with_data assert 0.0 == 0.00424
netguard: 20 blocked attempts from cm13/cm14 (curl_cffi egress to sonyworld.bh / shopalmoayyed.com products.json) - the SAME attempt the existing tests/test_retro_w1_3.py::test_pin_flag_off_both_compare_entries_never_read_the_openai_breaker shows at base; counted, blocked, not failed.

## Pins baseline (CM14)
[pyt] tag=cm-base-pins start=2026-10-09 17:12:18 end=2026-10-09 17:12:27 elapsed=9s bound=600s status=OK rc=0 ; 110 passed, 3 warnings.

## No git write, no production file, no mutation lock created (no mutation run).
