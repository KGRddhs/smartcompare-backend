## Retro-fix R-W18 (W1-8 adapter-drop visibility (#143, merged in session 65 without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**LOGGING ONLY, UNFLAGGED:** no price, no return value changes (pinned through the real `_get_price` / `fan_out_price_lookup` / `_timeout_none` with fixture-driven return-value assertions on every changed function).

**Verdict:** adversary round 0 DEFECTIVE (major: the per-scraper `[ADAPTER DROP] fanout:<kind>:<domain>: ERROR <Type>` lines could never fire because every fetch layer swallows transport exceptions before the scraper's except branch) -> fix round (ruling option b: a scraper whose fetch returns NO HTML now logs one `FETCH-FAIL` drop line, so a real transport failure is visible where it is observable; `pending=` is the true still-pending count via a module-level `_count_finished` wrapper; `_safe_exc` rewrites every `<scheme>://` token with a bounded scheme quantifier and strips userinfo up to the last `@`) -> adversary round 1 **SOUND** (6 unpinned minor branches recorded, no code defect; every return value driven through the real functions unchanged).

**Gates:** 47 unit nodes green (`tests/test_retro_w1_8.py` + `tests/test_adapter_drop_visibility.py`) on the pinned venv under a process-wide netguard (0 attempts); the 152-file comm set base == head (the base's 2 failures only); the census test now requires every `_timeout_none` call site to pass a distinct non-default label.

**Stated limits / follow-ups:** (1) the SLOW-MISS threshold stays at the ruled `adapter_inner_ceiling() - 0.5` (8.5 s at the default 9.0 s ceiling), so unbxd and noon - whose inner clamp is 8.0 s - can never produce a SLOW-MISS for a single-hop swallowed inner timeout; follow-up W1-8e keys the threshold on the adapter's own clamp; (2) socks5:// and bare `api_key=` tokens outside a URL are outside `_safe_exc`'s scope (stated); (3) the six surviving mutants are unpinned minor branches (a `#` fragment userinfo edge, a shared-counter-across-waves edge, the captured-vs-recomputed consume bound, the measured-vs-reported elapsed, the 0.05 s wrap margin pinned loosely) - test-hardening follow-up W1-8f.

**Canary (W5):** the `[ADAPTER DROP]` and `[FANOUT] wave=` INFO lines are grep-stable, one line each; `failed_count` keeps its semantics.

---

fix(price): make adapter and fan-out drops visible and bounded (R-W18, W1-8 retro); logging only, unflagged

DEFECTS (from the retro adversary review of PR #143, reproduced as probes P1-P5, then from the R-W18 green adversary):
- W1-8b: fan-out fetch failures were invisible at INFO. The retro review's premise was that `_curl_scraper`, `_firecrawl_scraper` and `_scrapedo_scraper` catch their fetch exception at DEBUG. That premise is only half right. Every fetch layer swallows transport errors before the scraper sees them:
  - `curl_fetch_html_same_site` logs a WARNING and returns None.
  - firecrawl and scrapedo return `(None, 0)` or `(None, <status>)`.
  So the scraper `except` branch only ever sees a bug. The green adversary drove the real stack, stubbing only `curl_cffi.requests.get` or `httpx.AsyncClient.post/get`, and got zero `[ADAPTER DROP] fanout:` lines for a wave where every fetch failed. `failed_count` stays 0 for these failures and nothing reads it.
- W1-8c: the three consume `except asyncio.TimeoutError` branches (sitemap, jsonapi, the `_new_adapter_specs` loop) are silent. `_timeout_none` cannot see an inner timeout the adapter swallowed. It also logs a TimeoutError the adapter raised 10 ms in as `TIMEOUT after 10.0s`.
- W1-8d: the ERROR drop line writes `str(exc)` verbatim. Probe P4 produced a 200,136-character record with a proxy password and a raw newline.
- Wave TIMEOUT line: `pending=` reported the wave size, not the count still pending (reproduced: `pending=4` with 3 of 4 finished).

FIX (app/services/structured_comparison_service.py only; no return value changes):
- Per-scraper fetch failure, the PRODUCTION shape. One INFO line per failed scraper:
  - `[ADAPTER DROP] fanout:curl:<retailer_domain>: FETCH-FAIL no-html` when fetch_page_price returns None, meaning no HTML was obtained: a transport error, a wall, a non-2xx response or a blocked URL. `{"_got_html": True}` is a MISS and stays silent.
  - `[ADAPTER DROP] fanout:<firecrawl|scrapedo>:<retailer_domain>: FETCH-FAIL status=<n>` when the service returns no HTML with a non-200 status. 0 means transport timeout or error, 429/503 mean throttle, 403 means wall. A 200 without usable HTML is a miss and stays silent.
- Per-scraper escaped exception (a bug above the transport): `[ADAPTER DROP] fanout:<kind>:<retailer_domain>: ERROR <Type>: <_safe_exc text>`, replacing the DEBUG `{url} raised` lines. Both token families carry the retailer label as the scraper receives it, never the scraped URL.
- Per-wave summary after fan_out returns: `[FANOUT] wave=<curl|render> completed=N failed=N cancelled=N elapsed=S`, where completed = wave size - failed - cancelled and elapsed is the measured wave wall time.
- Wave budget TimeoutError: `[FANOUT] wave=<kind> TIMEOUT pending=N elapsed=S`. N is exact: the call site wraps each scraper in `_count_finished`, which counts a return or a raise and never counts a cancellation. The wrapper returns or raises exactly what the scraper does, so fan_out's best, alternates and counts are identical.
- Consume branches: `[ADAPTER DROP] <sitemap|jsonapi|woo|salla|occ|...>: CONSUME-BOUND after <bound>s`, with the bound actually waited under, captured with a walrus at the existing `_consume_bound()` call.
- `_timeout_none` is timed with time.monotonic():
  - `TIMEOUT after <elapsed>s` only when elapsed >= timeout - 0.05; any earlier TimeoutError is `ERROR TimeoutError (adapter-raised)`.
  - `SLOW-MISS after <elapsed>s` when the adapter returns None at or after adapter_inner_ceiling() - 0.5.
  - Fast misses and every hit stay silent. Cancellation is still never caught and never logged.
- New local `_safe_exc(exc)`: it rewrites every `<scheme>://<token>` (any scheme, so http, https, socks5 and so on, with a bounded scheme match so it stays linear).
  - URL userinfo is stripped up to the LAST '@' in the token, so a '@', '/' or ':' inside an unencoded password cannot leak.
  - The query string and fragment are dropped; host and path are kept.
  - When the text before that '@' holds a '?' or '#', the token is replaced by `[redacted]`. That '@' could sit in a query or in a password, and the two cannot be told apart.
  - Every line break (including U+2028/U+2029 and \x0b) becomes one space. The text is scrubbed before it is truncated to 200 characters.
  - It is applied to the `_timeout_none` ERROR line and to the fanout ERROR lines. The W1-1 Sentry helper was measured unfit: it keeps `api_key=` and never strips userinfo.

THE PRODUCTION SIGNAL. `failed_count` keeps its semantics and stays 0 for real fetch failures. The production failure signal is the per-scraper `[ADAPTER DROP] fanout:` lines: FETCH-FAIL for a fetch that got no page, ERROR for an escaped bug. The W5 STEP-0 canary must count `[ADAPTER DROP] fanout:` lines (bucketed by FETCH-FAIL status / no-html vs ERROR) plus `CONSUME-BOUND`, `SLOW-MISS` and `TIMEOUT` lines, not failed=. The service-layer WARNING lines (`[PRICE] curl_fetch_html_same_site failed for <url>`, `[FIRECRAWL] Timeout`, `[SCRAPEDO] Timeout`) still fire unchanged and still carry the full URL (untouched, out of scope).

FLAG ROW: none. The fix is unflagged because the reviewer found silent drops with no legitimate reader, and the change only adds log lines. Every changed function's return value is pinned by fixture-driven assertions. The call-site wrapper is pinned return- and raise-identical through the real fan_out.

ACTIVATION GATE: live on deploy; nothing to flip. Before reading W5 canaries off these lines, watch INFO volume during the first slow-source episode. The expected volume is:
- one FETCH-FAIL line per curl URL that got no HTML (404 dead slugs included), plus one per failed render call;
- at most one line per dropped adapter;
- up to 2 [FANOUT] lines per product.
Volume is UNMEASURED. price-warmer runs stale 2026-09-02 code and emits none of this until redeployed.

EVIDENCE:
- Unit: tests/test_retro_w1_8.py plus tests/test_adapter_drop_visibility.py give 47/47 on the pinned venv with an autouse zero-network guard plus a process-wide netguard plugin. The result is the same 47/47 under ENABLE_GENUINE_PRICE_PRIORITY, ENABLE_NOT_A_PDP_FILTER, ENABLE_PRICE_PARSE_OFFLOAD, ENABLE_CONVERTED_PROVENANCE_STAMP (each alone) and all four on.
- Real-stack pins: a curl_cffi Timeout through the real curl_fetch_html_same_site, fetch_page_price, _curl_scraper and fan_out gives one FETCH-FAIL line per scraper. httpx ConnectTimeout through the real firecrawl/scrapedo services gives `FETCH-FAIL status=0`. The wave TIMEOUT through the real _get_price and fan_out gives `pending=1` for 3 finished and 1 hung.
- Mutation matrix: 60/60 KILLED from sha-verified byte snapshots in a scratch copy, with an unmutated control passing. It covers the adversary's M/N list re-run at HEAD, with re-expressed anchors where the regex moved, plus the fixer's F01-F17.
- Comm gate: the 152-file module-reference set under the netguard plugin gives 2 failed / 3963 passed, identical to base 1c6f6796. branch-only-NEW is empty, and both failures are in tests/.pre_impl_failures.txt.
- Lint: ruff E9,F63,F7,F82 and py_compile are clean.

HONEST LIMITS:
- SLOW-MISS keys on adapter_inner_ceiling() - 0.5, as ruled. adapter_inner_ceiling() defaults to 9.0 s, so the threshold is 8.5 s. unbxd and noon clamp their inner fetch to adapter_timeout(8.0) = 8.0 s, so their single-hop swallowed inner timeout returns None at about 8.0 s and stays SILENT. Adapters at the 9.0 s clamp are covered (woo, salla, occ, magento_gql, rest_json, brightdata). Covering unbxd/noon needs a re-ruling of the threshold (for example, min(ceiling, the adapter's own clamp) - 0.5).
- `FETCH-FAIL no-html` for curl is inferred from fetch_page_price returning None. Two other paths also return None and would be mislabelled:
  - a content-safety drop inside fetch_page_price, which logs its own `[content_safety]` line first;
  - with ENABLE_NOT_A_PDP_FILTER on (default OFF), a fetched page classified not-a-PDP.
- A render `FETCH-FAIL status=404/410` means the provider or upstream returned no page. The line reports the status, and the reader decides whether it counts as load.
- `_safe_exc` covers URLs of the form `<scheme>://`. A bare `api_key=...` outside a URL, and percent-encoded credentials, are not rewritten (the enclosing URL's query is dropped, which covers the common case). A fanout ERROR line keeps any host and path inside the exception's own text.
- `<retailer_domain>` is the harvest label (it can be a subdomain); no eTLD+1 is computed.
- CONSUME-BOUND names the family, not which sources in it were still pending (the cancelled per-source tasks stay unlogged by design).

FOLLOW-UPS, not in this unit:
- Measure log volume on the first canary.
- Re-rule the SLOW-MISS threshold for the 8.0 s clamp adapters (unbxd, noon).
- Scrub the service-layer WARNING lines, which log full URLs (price_service / firecrawl_service / scrapedo_service).
- The PR #143 body's byte-identity citation is environment-dependent. Future claims should cite a same-env parent-vs-head pair only.
- Redeploy price-warmer to pick this up.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
