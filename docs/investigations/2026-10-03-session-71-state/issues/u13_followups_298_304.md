=== TITLE: U13c (client): camera /image/identify 401 -> refresh -> retry once
=== LABELS: mobile,launch
## Context
U13 (PR #U13PR) puts the paid routes behind `ENABLE_COMPARE_AUTH_REQUIRED`. The six app routes accept a signed-in user; the camera path (`POST /api/v1/image/identify`) is driven by a raw fetch in the client that has NO 401 refresh-and-retry, unlike the axios interceptor used by the text and URL compares. With the flag ON an expired access token on the camera path gives the generic camera error instead of a transparent refresh (stated limit L8 of the unit).

## What to build
- On a 401 from `/image/identify`, refresh the session once (the same refresh the axios interceptor uses) and retry the upload once; a second 401 surfaces the sign-in prompt, not the generic camera error.
- Pin it with a unit test on the camera service (401 then 200 -> one refresh, one retry; 401 twice -> sign-in state; no retry on any other status).

## Why it matters
Does not gate the flag flip (the token is refreshed by any other axios call), but it must merge before the U10 production store build so App Review never sees a dead camera after a long idle.

## Acceptance
- jest green, tsc clean, no snapshot change.
- OTA-capable; no native dependency.

=== TITLE: Per-user limiter key on authenticated routes (the per-IP bucket is not a spend control)
=== LABELS: backend,security
## Finding (session 71, measured 2026-10-02/03)
Production served 322 anonymous `/api/v1/text/compare` calls in 27 active minutes from 155 rotating addresses with no 429. Railway shows `FORWARDED_ALLOW_IPS`, `RATELIMIT_ENABLED`, `ENABLE_PROXY_AWARE_RATELIMIT` and `WEB_CONCURRENCY` absent, one replica: the slowapi bucket is keyed on a peer address that varies across requests, so the 10/minute limit never trips for a rotating caller. The CLAUDE.md sentence that calls the proxy-IP key "one deployment-wide bucket" is wrong (U13 stated limit L2 / ruling UR13).

## What to build
- With U13 ON every paid call carries a user id or the admin credential: key the limiter on the user id (fallback: the admin credential hash, then the address) for the ten paid routes, behind its own default-OFF flag with flag-OFF byte identity.
- Correct the CLAUDE.md limiter sentence.
- Pin: two users from one address get separate buckets; one user from two addresses shares one bucket; anonymous refusals never consume a bucket (already pinned by U13 T19).

## Not in scope
Admin-key guessing on these routes is a separate limit (U13 L6, same class as the existing admin routes).

=== TITLE: Live and integration tests that will 401 once ENABLE_COMPARE_AUTH_REQUIRED is on
=== LABELS: tests,backend
## Context
U13 (PR #U13PR, spec correction C10) found these files call the paid routes against a live base URL with no credential. They are not collected in CI (live markers), but once the flag is ON in production they return 401 `AUTH_REQUIRED` and look like outages:

`tests/test_integration.py`, `tests/test_two_input_shape.py` (TestLiveRailwaySmoke), `tests/test_d2_spec_parity_per_category.py`, `tests/test_spec_parity.py`, `tests/test_unified_search.py` (TestCostTrackingLive), `tests/test_cohort_personalization_load.py`, `tests/test_bundle_c_integration.py`, `tests/test_bundle_e_integration.py`, `tests/test_lane2_integration.py`, `tests/test_scoring_v2_all_nine_categories.py`, `tests/perf/test_latency_bench.py`, `tests/post_deploy/bundle_c_acceptance.md`, and `tests/integration/bundle-e-smoke.sh` probe 4 (`AUTH_ARG`).

## What to do
Give each live path the same opt-in the five harness scripts got in U13: send `X-Admin-Key` only when `HARNESS_SEND_ADMIN_KEY` is truthy and `ADMIN_API_KEY` is set (one shared helper), or a bearer where the test already logs in. Never print the value. A future `cron_eval_nightly` service needs its own credential (C8).

=== TITLE: Raw query and URL logging at INFO in text_routes and url_routes
=== LABELS: backend,privacy
## Context
Pre-existing (U13 stated limit L10): `app/api/text_routes.py` and `app/api/url_routes.py` log the caller's raw query string and URLs at INFO. With U13 ON anonymous callers no longer reach those lines, but signed-in users do, so the production log stream carries user search text and product URLs.

## What to do
- Replace the raw values in the INFO lines with a length and a stable hash (or the comparison id once it exists), keeping the DEBUG lines for local runs.
- Pin with the existing log-hygiene test pattern (`tests/test_openai_key_log_hygiene_s69.py` is the model).

=== TITLE: Multipart parsing of /image/identify runs before the U13 guard
=== LABELS: backend
## Context
On fastapi 0.141.1 a router-level dependency runs AFTER body parsing for a multipart handler, so an anonymous `POST /api/v1/image/identify` still costs the full upload parse (CPU and memory) before the 401 (U13 stated limit L5; JSON bodies are the same for the 422 path). No paid work runs.

## What to do
Measure the cost of a maximum-size anonymous upload with the flag ON; if it matters, move the credential check into a middleware or a pure-header dependency that runs before the body is read for that one route, keeping the U13 refusal envelope byte-identical. Pin with the U13 test conventions (hermetic stubs, flag matrix).

=== TITLE: Smoke accounts in production use a password that is public in the repo
=== LABELS: security
## Context
U13 stated limit L1: `scripts/bundle_d_prod_smoke.py` registers throwaway accounts in production with a password that is readable in the public repo history. How many such accounts exist in production is not measured. With U13 ON a free account is bounded by the free tier (3 lifetime-free, 3/day, 10/month), so the exposure is small but real.

## What to do
- Count and delete the existing smoke accounts (an admin task; the account-deletion path of U8b erases them fully once migration 043 is applied).
- Make the smoke password a required environment value (never a default in code), and have the probe delete its account at the end of the run.

=== TITLE: admin_routes.verify_admin_key treats a whitespace-only ADMIN_API_KEY as configured
=== LABELS: backend,security
## Context
Found by the U13 security adversary (measured under TestClient): with `ADMIN_API_KEY=" "` and the header `X-Admin-Key: " "` `verify_admin_key` passes and the guarded route runs. Under uvicorn/h11 the header whitespace is stripped, so the same request is refused there (inferred, not measured). It needs an operator misconfiguration, so it is low severity, but it affects every admin route, not only U13.

## What to do
In `app/api/admin_routes.py`, treat a configured key that is empty after `strip()` as unset (403 on every attempt), and pin it. U13 reuses `verify_admin_key` verbatim (ruling D3), so the fix lands in that one function.
