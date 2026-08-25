# Audit implementation — session handoff (2026-08-25)

Second session on the full-repo audit of `c630436`. **Seven PRs merged; `main` is now `b83bf7b`
and deployed.** This file is the pick-up point.

## Headline: CI went from 176 failures to 15

| | backend-tests | backend-lint | dependency-audit | frontend-typecheck |
|---|---|---|---|---|
| `c630436` (before) | ❌ 176 failed / 9,359 passed | — | — | ✅ (continue-on-error) |
| `b83bf7b` (now) | ❌ **15 failed / 9,653 passed** | ✅ | ✅ | ✅ |

CI had been red on every run since at least 2026-07-07. Two root causes, both now closed: a missing
`pillow` dev dependency, and the 35 RED-by-design `test_value_math.py` stubs that CI never excluded.

The remaining 15 are tracked in **#89** with root causes already diagnosed — do not re-derive them.

## What merged

| PR | Issue | Effect |
|---|---|---|
| #82 | #46 | Compiled universal dependency lock + CI drift gate. Deploys are reproducible; `--universal` markers verified installing on Railway's Linux. |
| #88 | #48 | Credential neutralisation in conftest. **This is what removed 126 of the failures.** |
| #86 | #49 | CI gates: known-red containment, black lint, pip/npm audit, coverage floor, weekly live-adapter workflow. |
| #85 | — | Prior handoff + the three repo traps. |
| #84 | #59 | Subtype spec reconciliation + enriched-specs caching (stops paying twice for extractions). |
| #83 | #58 **(Step 1 only)** | Model ids resolve from `app/services/model_config.py`, env-overridable. Defaults unchanged. |
| #87 | #60 | Serper budget gate — **opt-in**, inert until `SERPER_LIFETIME_LIMIT` is set. |

## Nothing merged is active until env vars are set

All three behavioural changes ship deliberately inert:

- `SERPER_LIFETIME_LIMIT` — arms the budget gate. Unset = no-op on the current config.
- `OPENAI_MODEL_VERDICT` / `OPENAI_MODEL_VISION` — the model flip. **Do not set without a live
  smoke test.** GPT-5 rejects `temperature=0` outright (the verdict's determinism A/B depends on
  it), requires `max_completion_tokens`, and bills invisible reasoning tokens against that same
  budget, so carrying `1000` over can return empty content with `finish_reason="length"`. The
  shims prevent the 400s; they cannot restore determinism. Worth ~$0.0224 → ~$0.0030 per
  comparison once verified.
- `--cov-fail-under` is deliberately 60 against a locally-measured 78. Raise it to the number CI
  now reports, rounded down.

## Two live blockers — nothing else matters while these are down

Observed directly in test runs this session:

- **Serper → `403 Unauthorized`** on every `/search`. A $50 Starter pack is 50,000 credits with
  6-month validity and no subscription; the free trial is 2,500 one-time, ≈180 cold comparisons.
- **OpenAI → `429 Too Many Requests`.** Set auto-recharge WITH a monthly cap — that removes the
  hard-stop outage while keeping a spend ceiling.

## Scraper tooling: evaluated and rejected (2026-08-25)

Community advice recommended Firecrawl + crawl4ai, and claimed `Socialcrawl.dev` "works fine".
All three researched; none change the standing decision (keep the hybrid, invest in discovery).

- **SocialCrawl.dev — reject, no trial needed.** It *resells Firecrawl*; its own status page says
  "Firecrawl is the upstream for scrape, search, map, extract, crawl…". Same tool that returned a
  3KB Cloudflare block page on bolo.bh/boutiqaat, plus a reseller hop and ~3–4× markup. It is also
  ~96% a social-media API (web = 16 of 403 endpoints).
- **crawl4ai — do not adopt.** Its "undetected browser" *is* patchright + playwright-stealth, both
  installable without it. The one independent benchmark scores **curl_cffi 26 OK vs patchright
  25 OK — the tool this repo already uses ranks higher.** Its non-browser path is `aiohttp` (stock
  TLS), strictly worse than curl_cffi impersonation. Nothing on IP reputation, which is the actual
  sephora.me variable. An RCE/SSRF/auth-bypass class was fixed 2026-06-01 in the Docker server you
  would deploy; 123 unmerged PRs; 78% of commits from three authors.
  **One idea worth stealing:** its `AsyncUrlSeeder source="cc"` uses **Common Crawl as a discovery
  channel** — a different corpus from the sitemap index. Prototype natively against the CC index
  API (~1 day); do not adopt the framework.
- **Self-hosting the Akamai residual:** at ~2,000 walled PDPs/month the cash gap is ~$10/month
  (Zyte $32–60 vs self-host $21–28) but self-hosting adds $100–400/month of maintenance.
  Residential bandwidth alone is $0.005–0.013 per rendered page — the same order as Zyte's entire
  per-page price — and Zyte bills only *successful* responses. The win is **deleting Firecrawl and
  Scrape.do**, not building a browser fleet: Firecrawl's proxies are NL/US-only, so it structurally
  cannot render a Bahrain-localised page.

## Standing environment facts (do not rediscover)

1. **`pytest tests/` HANGS.** `magento_graphql_service.py:275` and `noon_service.py:170` fetch live
   retailer sites in executor threads the pytest timeout cannot kill (that is #70 reproducing
   in-suite). `tests/test_rate_limiting_complete.py` also does a real GET. Run targeted file sets,
   excluding adapter/network-heavy files.
2. **`app/config.py` is an import trap** — seven required pydantic fields and `Settings()` at import,
   so importing it raises `ValidationError` wherever env is absent. Never add config there;
   `app/services/model_config.py` is the pattern to copy.
3. **The comm-gate baseline must match the environment the change is about.** Comparing #48 against
   a *credentialed* main showed two false regressions; against main with `.env` parked — the
   environment CI actually runs in, which reproduces the 176 count exactly — it was zero.
4. Two tests pass **only because they reach live production Supabase**
   (`test_invitee_quiz::test_invalid_token_format_does_not_crash`,
   `test_supplement_branch_genuine::test_cde2_...`). Tracked in #89.

## Suggested order next session

1. **#89** — the last 15 failures. Turning `backend-tests` green is what lets it become a required
   check, which every later merge benefits from.
2. **#50 → #51 → #52** — the price-truth cluster. #50 is the P1: a foreign amount can currently be
   relabelled BHD 1:1 and served as genuine.
3. **#53** — the 30-day `nogenuine` sentinel is never deleted, so a resolved genuine price decays
   back to a stale estimate.
4. **#65, #64** — the dead behavioural-personalization layer, and SSE failures being logged as
   successes and charged against freemium quota.
5. **#75** — activate the owned sitemap discovery channel. This is the own-scraper investment the
   costing endorsed; the code is written and inert.
