# Production traffic finding — anonymous compare burst on 2026-10-02 (measured 2026-10-03)

Measured by the session-71 orchestrator from three sources: the Sentry connector (org `qaren-rr`, region `de.sentry.io`), Railway HTTP request logs of the `web` deployment that was live at the time (`d88b5957`, commit `94c097cd`, 2026-09-29T23:50Z → 2026-10-03T03:35Z, 4,870 requests), and the application log for 09:25–09:34 UTC. No secret was read or printed; key-shaped strings were redacted before any log line was shown.

## What happened

| Fact | Measurement |
|---|---|
| Requests to `/api/v1/text/compare` in 77 hours | 322 (315 GET, 7 POST) |
| When | 2026-10-02 09:25 → 10:5x UTC (12:25–14:00 AST), 27 active minutes; one more call 2026-10-03 01:58 UTC |
| Peak rate | 51 requests in one minute |
| Source | 155 distinct IPs: 133 in `154.85.0.0/16`, 21 in `156.240.0.0/16`, 1 at `31.77.203.199`; Sentry geolocates the caller to Singapore |
| User agents | `python-httpx/0.28.1` (242), `python-requests/2.34.2` (80) — the exact versions pinned in this repo's `requirements.txt` |
| Authentication | none (anonymous) |
| Responses | 318 × HTTP 400 (the parse-failure copy, because OpenAI is out of credits), 3 × 200, 1 × 422; **no 429** |
| Queries | a small set repeated (one 31-character query 47 times, a 23-character one, others 11–13 times each; lengths 18–60). 31 and 23 characters are the lengths of `iPhone 15 vs Samsung Galaxy S24` and `iPhone 15 vs Galaxy S24`, the example pairs in this repo's docs. The log stores a hash and a length, not the text. |
| Related probes | `GET /api/v1/share/v1/models` and `GET /api/v1/auth/social/apple/callback/v1/models` from `31.77.203.199` (`python-httpx/0.28.1`) — the shape of a scanner looking for OpenAI-compatible endpoints |
| Sentry | 370 backend error events in that window (340 on the OpenAI 429 issue `PYTHON-FASTAPI-R`) |

This machine's public IP today is `193.188.113.135`; it made exactly one request in the period (my `/health` probe). The burst did not come from this machine's direct connection.

## What it means

1. **The rate limiter did not limit it.** The compare route is decorated 10/minute; 51 requests in one minute returned no 429. A caller with rotating IPs is not bounded by a per-IP limiter at all, and here even the shared bucket did not engage.
2. **Anonymous compare is open to anyone, and the repo is PUBLIC** (`KGRddhs/smartcompare-backend`, visibility `public`, 0 forks). The production URL, every route, the eval/smoke scripts that target production by default, and the example queries are readable by anyone. The caller is either one of Ahmed's own cloud agent sessions running the repo's harness, or a third party using the public repo. The logs cannot tell which.
3. **It cost nothing only because OpenAI is out of credits.** Each call failed at the first LLM step in about one second. With credits, each anonymous compare costs a modelled $0.023–0.031 plus search credits. The same burst completed would be roughly $7–10; the measured peak rate sustained would be about $70–95 per hour. A $100 top-up could be drained in about an hour.
4. **No existing flag closes this.** `ENABLE_ANON_USAGE_GATE` covers only `/text/quick` and `/image/identify` and is keyed on a header a script simply omits; `ENABLE_LLM_PREFLIGHT_BREAKER` acts only while OpenAI is failing; the proxy-aware limiter does nothing against 155 IPs.
5. **The mobile app is login-gated** (the review needs a demo account for exactly that reason), so requiring authentication on the compare routes would not affect real users.

## Second finding: no tester phone has opened the app since the OTA

The same 77-hour log contains **zero** requests with a mobile user agent and zero calls to `/api/v1/app/version`, `/auth/*` or `/usage/status` (the app calls these on open). The Sentry `react-native` project shows 0 errors and 0 spans in 30 days; its last issue is `REACT-NATIVE-D` on 2026-07-06. So the zero in Sentry is explained by no usage: whether mobile reporting works is still unmeasured, and the OTA `e2bde9c9` has not been pulled by any tester.

## Recommended decisions (Ahmed)

- **Before the OpenAI top-up:** choose prepaid with a low project budget and no auto-recharge (D8) until the compare routes require authentication.
- **New unit U13 (proposed, not started):** the compare, URL-compare and camera routes require an authenticated user behind a default-OFF flag; the repo's own harness scripts authenticate (a test account or the admin key). Flip the flag before funding OpenAI.
- **Repository visibility:** make it private, or accept it as public deliberately. Trade-off to check first: on a GitHub Free plan a private repository loses branch protection (the five required checks) and consumes Actions minutes.
- **Was the burst yours?** A Codex or Claude cloud session, or Husain, running `eval_runner` / the smoke scripts at 12:25–14:00 AST on 2026-10-02 would explain it.
