The session-68 reload audit (PR #207, merged as 4cff9bc1) found five test files whose `importlib.reload` leaves the module's objects REBOUND for the rest of the process. Values are restored; identity is not.

The session-68 reload audit (strong-reference `vars()` diff before setup / after teardown) found five test files whose `importlib.reload` leaves the module's objects REBOUND for the rest of the process. The values are restored, but the identity is not. Any module that bound a name at collection time then holds a stale object. None trips the #183/#185/#186 sentinel today and none moves a value, but each is the same class of hazard that produced #185:
- `tests/test_backend_cleanup.py::TestLegacyRoutesRemoved::test_main_imports_cleanly` reloads `app.main` (a NEW FastAPI `app`; 49 test files bind `from app.main import app` at module level)
- `tests/test_fan_out_budget_env.py` (6 tests) reloads `firecrawl_service` + `scrapedo_service` (`source_router` binds `scrapedo_service._super_enabled` lazily)
- `tests/test_m18_openai_tpm_sizing.py` (2 tests + fixture) reloads `openai_service` (new `client`; `image_routes` binds `identify_products`, 3 modules bind `get_client`)
- `tests/test_observability.py` (4 tests) reloads `sentry_service` (`app.main` binds `init_sentry`)
- `tests/test_supplement_branch_genuine.py` (2 tests) reloads `source_router` (the `Source` dataclass is replaced, so an isinstance check against the old class fails)
Fix per file: build a PRIVATE module instance via `importlib.util.spec_from_file_location` + `module_from_spec` under the real dotted name (the W0-3 pattern in `tests/test_cache_service_bounded_transport.py`), never touching `sys.modules`. `monkeypatch.setattr` does not apply where the test exercises import-time construction. Add each module to `tests/_hermeticity.py` only if a value-level item is needed.

### #185 exposure measurement
At base, one process ran `tests/test_platform_router.py` plus every later-alphabetical test file that mentions price_service. Result: 1 failed (l13 `test_fetch_uses_catalog_and_matches`), 2,773 passed, and 3 TestFetchShopifyPrice nodes made real curl_cffi GETs to shopalmoayyed.com. After this PR: 0 failed, 2,774 passed, and 0 network attempts from any test_shopify_discovery_l13 node (15 attempting nodes in that run, all in the baseline).

