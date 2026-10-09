## LINK-PERSIST: Link-mode comparisons are never persisted (billed, but no history row)

Found during the COST-METER spec review (session 74, finding F17; ruling CM12 filed it for the plan). Verified at main `4c0f3c99` on 2026-10-09.

### What happens

1. `POST/GET /api/v1/url/compare` (`app/api/url_routes.py:199-206`) fires `save_comparison_and_track_cohort(full_response=result, query=f"{url1} vs {url2}", input_type="url", ...)` for every signed-in Link-mode compare while `ENABLE_PAID_ROUTE_METERING` is on (it is ON in production since 2026-10-03).
2. `database_service.save_comparison` (`app/services/database_service.py:413-431`) gates every write on `_validate_renderable(full_response)`.
3. `_validate_renderable` (`database_service.py:303-320`) requires `payload["metadata"]["query"]` to be truthy.
4. `url_extraction_service.compare_from_urls` (`app/services/url_extraction_service.py:680-689`) returns `{success, products, comparison, winner_index, recommendation, key_differences, category_used, source_urls}` and NO `metadata` key at all.

So the gate returns False on every Link-mode payload, `save_comparison` logs `skipping unrenderable payload` and returns None, and the `comparison_renderable=false` Sentry tag fires on every Link compare. Meanwhile `record_lifetime_comparison` (`url_routes.py:208-211`) still runs, so the user is charged a comparison credit for a result that never reaches History, Smart Pick or Share.

### Consequences

- History and `/home/smart-pick` never show a Link-mode compare; the user cannot reopen or share it.
- The persisted-comparisons metrics (and the COST-METER dashboard, which reads persisted rows) exclude the whole Link path, so Link-mode spend is invisible there (COST-METER ruling CM6 names this exclusion in the dashboard note).
- Every Link compare raises the `comparison_renderable=false` warning in Sentry, which drowns a real renderability regression.

### Fix sketch (own unit; spec + adversarial review first)

- `compare_from_urls` adds `metadata` (at least `query` = the two product names or the two URLs, `category_used`, `partial`, `stage_timings_ms` if available) in the same shape the text path builds in `response_builder.build_comparison_response`, or routes its final assembly through that builder so the Link path carries `overview`, `scoring`, `metadata` like the text path.
- Pins: a Link-mode payload passes `_validate_renderable`; the saved row carries `input_type="url"`; a URL compare with fewer than two products still does not persist; the public share view strips the same keys as for text compares.
- Decide (owner call) whether `metadata.query` for Link mode shows the URLs or the extracted product names in History.

### Out of scope here

The anonymous half of `/url/compare` (issue #128) and the DNS-on-loop residual of U13e are separate.
