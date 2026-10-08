# FANOUT-STARVE (new backend unit, accepted 2026-10-08) - brief for the spec workflow

Problem (measured in session 74, ledger 14:07-14:28): every compare ran to the 30 s hard cap and Serper connect-timed out on every compare day since 2026-10-03. Not the network (in-container probes: Serper 0.03 s, 16 hosts resolve + connect < 0.4 s). Two process-internal causes: (1) uvicorn runs on uvloop (pinned 0.22.1, no --loop flag), whose getaddrinfo uses libuv's 4-thread pool (UV_THREADPOOL_SIZE unset), so httpx lookups (Serper, OpenAI, Bright Data, page scrapes) queue past the 3 s fail-fast connect budget under the fan-out; (2) the 40-thread default executor (app/utils/executor.py) saturates under ~30 blocking curl_cffi adapter fetches per compare (SLOW-MISS / TIMEOUT 11-19 s). Also found: the Bright Data fallback answers 401 Token expired (an owner renewal) and its breaker trips silently (WARN only, no Sentry event); Shopify stores answer 429 to the Railway egress IP.

Runtime levers set on Railway `web` with the owner's word (reversible): ADAPTER_EXECUTOR_MAX_WORKERS=96, UV_THREADPOOL_SIZE=64, SERPER_CONNECT_TIMEOUT=8. Result: canary 4 PASS, Serper ConnectTimeout 0, adapter stalls 3-4; but the 15 s price race and the 8 s specs race still expire on every product and 4 of 6 prices stay pending_genuine.

Scope for the unit (spec + adversarial review first):
1. Make the levers code truth: a resolver pool decision (dedicated `getaddrinfo` executor for httpx, or `--loop asyncio` with a measured comparison, or documenting UV_THREADPOOL_SIZE in railway.json/Procfile) with a hermetic pin that the DNS path does not share the adapter pool.
2. A fan-out semaphore for the blocking adapter fetches sized against the executor, with a pin.
3. Bright Data expiry: a Sentry-captured error (not WARN) on 401, a breaker-trip event, and a health field; a runbook line for the owner renewal.
4. Measurement, not guesses: a stage-timing table (serper_shopping, adapters, race, cap) before and after, from the canary pairs, via the existing [PRICE_SUBSTAGE] lines.
5. Out of scope: the Shopify 429 egress question (a separate price-coverage unit), the 30 s cap value itself (product call).
Acceptance: canary pairs below the hard cap with at least one price amount per product that has a BH retailer; flag-OFF byte-identity on the price path where a flag is used.
