# Pre-impl free-unit failure baseline (GENERATED — do not hand-edit)

<!-- BASELINE_COUNT: 14 -->

> **GENERATED FILE.** This mirror is rendered from `tests/.pre_impl_failures.txt` by `scripts/gen_baseline_mirror.py`. Do not edit it by hand — re-capture the baseline, then regenerate. `tests/test_ci_gates.py` re-derives the count and id set from the .txt and fails if this file drifts (the M13-17 regression: the mirror once claimed 49 against the file's 48).

The free-unit regression gate (`scripts/regression_gate_diff.py`) is a SUBSET check: a branch is GREEN iff its FAILED set (minus `NETWORK_FLAKY_EXCLUDE`) is a subset of the 14 node ids below. The baseline was RE-CAPTURED 2026-09-01 (M13-17) from a clean, credential-free free-tier run — the exact state of CI and a fresh clone — so `current - baseline` is empty on an untouched tree.

| # | Failing node id |
|---|-----------------|
| 1 | `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` |
| 2 | `tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully` |
| 3 | `tests/test_backend_cleanup.py::TestDeadFunctionsRemoved::test_unused_imports_cleaned` |
| 4 | `tests/test_camera_vision.py::TestIdentifyProductsMocked::test_empty_product_fields_normalized` |
| 5 | `tests/test_camera_vision.py::TestIdentifyProductsMocked::test_malformed_response_returns_error` |
| 6 | `tests/test_camera_vision.py::TestIdentifyProductsMocked::test_successful_identification` |
| 7 | `tests/test_database_service.py::test_save_comparison_skips_when_not_renderable` |
| 8 | `tests/test_extraction_prompt_bundle_c.py::test_response_builder_strips_inference_source` |
| 9 | `tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest` |
| 10 | `tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction` |
| 11 | `tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities` |
| 12 | `tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys` |
| 13 | `tests/test_referral_e2e.py::test_e2e_share_creates_invite_and_grants_loop1_credit` |
| 14 | `tests/test_supplement_branch_genuine.py::TestCatalogSupplementSourceAttribution::test_cde2_attributes_catalog_supplement_domain_when_flag_on` |
