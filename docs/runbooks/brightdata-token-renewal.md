# Runbook: Bright Data token renewal (BRIGHTDATA_API_KEY)

Owner: Ahmed. Written 2026-10-09 (FANOUT-STARVE D6, pre-ruling F3). The Bright Data SERP
fallback is ARMED on the `web` and `price-warmer` services (ENABLE_BRIGHTDATA_FALLBACK=true,
the key and the zone set, ENABLE_BRIGHTDATA_BUDGET_GATE=true since 2026-09-24). When the
token expires every fallback call answers 401 and a compare silently loses its last search
rung (canary 6, 2026-10-08).

## Symptom lines (Railway log of the affected service)

- `[brightdata] auth rejected status=401 type=HTTPStatusError -- every fallback call fails with 401 until BRIGHTDATA_API_KEY is renewed (owner)` (or the same line with `403`) -- ONE ERROR per process per status, hence one Sentry event (python-fastapi project) under the U8d ERROR-only policy. Each status has its own constant message, so Sentry shows ONE issue PER STATUS (a 401 issue and a 403 issue), not one issue for both. The message never carries the query, the response body, the zone or the key.
- `[brightdata] HTTP 401 for '<query>': auth rejected (body withheld)` -- one WARNING per call (Railway log only; Sentry does not receive WARNING lines).
- `[CIRCUIT] brightdata breaker TRIPPED after N failures` -- the budget gate's breaker (api_budget_service), WARNING, after three failures (`CB_FAILURE_THRESHOLD = 3`); grep-stable.
- `GET /health` carries `"brightdata_auth": {"last_status": 401, "at": "<UTC timestamp>"}` once a process saw a 401/403; the key is absent on a process that saw none.

## Renewal

1. Bright Data dashboard -> the SERP API zone (`serp_api1`) -> API token: create or renew the token. Never paste it into a chat, a doc, a log or a transcript.
2. Set it by NAME on both services from a real terminal (Git Bash), in a form that keeps the token out of the shell history: read it at a silent prompt into a shell variable, pass the variable, then unset it. The history then holds only `$BD_TOKEN`, never the value:
   `read -rs BD_TOKEN` (paste the token at the silent prompt, then Enter)
   `railway variables -s web --set "BRIGHTDATA_API_KEY=$BD_TOKEN"`
   `railway variables -s price-warmer --set "BRIGHTDATA_API_KEY=$BD_TOKEN"`
   `unset BD_TOKEN`
   (Alternative: prefix each `railway` command with a space under `HISTCONTROL=ignorespace`, so the shell does not record it.) The token must never appear in a transcript, a chat, a doc, a log or a shell history; if it did, renew it again. A variable change redeploys `web`; `price-warmer` is off push-triggered deploys and picks the value up on its next run (or `railway redeploy -s price-warmer`).
3. Verify on the NEW `web` process: `GET /health` has no `brightdata_auth` key, and the first fallback call logs `[brightdata] parsed OK for ...` instead of the 401 WARNING. Only a Serper failure exercises the fallback; without one, the absence of the key and of the ERROR line on the new process is the proof.
4. Resolve the Sentry issue `[brightdata] auth rejected status=401 ...` (and the `status=403` issue if one was opened: one issue per status) with the renewal date in the comment.

## Notes

- The ERROR fires once per process per status, so a long-lived process logs it once; a redeploy, or every warmer run, logs it again while the token is still dead.
- Names only in any agent context: read variables with the names-only recipe of CLAUDE.md (`railway variables --service <svc> --kv | cut -s -d= -f1`); never print a value (principle 10).
- Rollback of this runbook's code (D6) is a plain revert; it is logging and one additive /health key, no response byte moves.
