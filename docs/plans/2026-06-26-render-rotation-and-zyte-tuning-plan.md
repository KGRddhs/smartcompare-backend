# Plan — Serper/Scrape.do rotation + Zyte render-tier tuning (2026-06-26)

Continues the genuine-price work. Prod `main` @ `dcf1734` (BH/GCC catalog ACTIVE,
Zyte tier shipped dormant). Three providers were dead/degrading; new keys supplied
this session.

## Provider state (verified this session)
| Provider | Old state | New key | Local-verified |
|---|---|---|---|
| Serper | depleted (`44e3b202`, 2645/2200) | `7de9c750…` | ✅ HTTP 200, fresh credits, counter absent (key-scoped) |
| Scrape.do | dead (401) | `963772…` | ⏳ A/B running (does `super`+`geoCode=bh` crack sephora Akamai?) |
| Zyte | **account suspended** (403 billing) | `e3374b…` (NEW account) | ⏳ A/B running (new key live?) |

Key facts:
- Serper counter + burn sentinel are **key-scoped** → the new key auto-starts fresh;
  no reset needed. Stale sentinels for dead keys (`05d552d7`/`44e3b202`/`696e4e57`)
  to be DEL'd for hygiene during deploy.
- Zyte/live-path is **gated OFF** (`ENABLE_ZYTE_RENDER` unset on Railway) → the
  render-tier never touches the 15s request clock; the off-clock seed writes the
  cache, live serves cache-first. So **Zyte needs NO Railway var** — only local.

## Step 1 — Serper rotation (restores specs/reviews/images + non-render prices)
- [x] `.env` synced to `7de9c750…`
- [x] new key liveness verified (direct probe)
- [ ] **Railway** (needs `railway login`): `railway variables --set "SERPER_API_KEY=…" --service web` → `railway redeploy --service web`
- [ ] DEL stale `budget:serper:burn_alert_fired:{05d552d7,44e3b202,696e4e57}` (hygiene)
- [ ] verify: cold prod `GET /api/v1/text/prices/iPhone+15+Pro?nocache=true` → Serper-live (real retailers, not `estimated`)

## Step 2 — Scrape.do rotation + render-provider A/B  ✅ DECIDED
- [x] `.env` synced to `963772…`
- [x] **A/B run** (`scripts/ab_render_providers.py`): Oud Wood → Zyte 77 (33.5s) AND
  Scrape.do super 77 via page_scrape (14.4s, 200, cost=25) → **Scrape.do super DOES
  crack sephora's Akamai wall**. But: Black Opium → Scrape.do 502 (transient); Dior →
  Scrape.do only had the search page (no price). Zyte returned structured prices in
  one call.
- [x] **RENDER PROVIDER DECISION: Zyte stays the sephora render provider.** Zyte does
  search→match→price in ONE call; Scrape.do can only render a URL you give it (no
  search) → a Scrape.do-only sephora path needs a separate PDP-URL discovery step.
  Scrape.do `super` is a proven BACKUP + the right tool for FUTURE render sources where
  we already have PDP URLs (namshi/Carrefour catalogs); at 25 credits/req on 900/mo
  (~36/mo) it is budget-tight for bulk seeding.
- [ ] **Railway** (needs `railway login`): `railway variables --set "SCRAPEDO_API_TOKEN=…" --service web` → redeploy (restores the existing Tier-1.5d page-render fallback for non-walled retailers — independent of the sephora decision)

## Step 3 — Zyte matcher fixes + no-fab HARDENING (CODE DONE, 33/33 tests green) + re-seed
Adversarial review Workflow (`wf_5211466b-4ee`) found REAL no-fab leaks (verify phase
rate-limited → dispatcher-gated the 18 findings from the transcript). The loose 0.5
overlap admitted flankers + near-names + bases. Replaced with a HARD identity gate.
- [x] concentration precision (EDP>Parfum; explicit-mismatch reject) — live-verified Oud Wood 77 not 158
- [x] **HARD product-identity gate** (`_identity_tokens` equality; brand+concentration-phrase+size+form stripped) — rejects flanker ("Black Opium Over Red"), near-name ("Ombre Nomade" vs "Ombre Leather"), base-for-flanker ("Dior Homme" vs "Dior Homme Intense")
- [x] form gate (sets/body-sprays) + transient-empty retry + terminal-4xx no-retry
- [x] **account-dead kill-switch** on 401/402/403 (fragile-trial protection: stops a 20-product seed loop hammering a suspended account) + honest docstring
- [x] `metadata.probability` deterministic tiebreak; `brand=` wired through the live cascade
- [x] 10 new no-fab/kill-switch regression tests (flanker-only→pend, near-name→pend, base→pend, wrong-brand-fragrance-list→pend, 402-terminal, kill-switch-stops-run, empty-twice→pend, probability tiebreak)
- **EMPIRICAL (live Zyte diag):** Dior Sauvage / Marc Jacobs Daisy / Viktor Rolf Flowerbomb = **sephora COVERAGE gap** — sephora.me returns makeup recommendations (overlap 0.0), the matcher correctly pends. NOT a matcher bug; NOT fixable by query reformulation (tested name-only + with-concentration). The lever for these is MORE walled sources (deferred), not tuning.
- [x] adversarial review Workflow VERIFY+RE-REVIEW re-ran (sequential, survived the burst): original findings all fixed/dismissed (13); the re-review on the hardened code found mostly no-fab-SAFE coverage edges + 1 real wiring gap (seed didn't reset the kill-switch → FIXED) + diacritic over-strictness (caught empirically first → FIXED with NFKD folding) + EDT-canonical (FIXED via EDP=EDT tie + probability tiebreak → Acqua di Gio picks the canonical EDT 44)
- [x] **re-seed DONE** (final matcher): corrected Oud Wood 77 (was 158), Black Orchid 55.5 (was 81.5), Acqua di Gio 44 EDT (diacritic-fix recovery), Good Girl 38 + Black Opium 85 (flankers flushed), Tobacco Vanille 77, Lost Cherry 100.5, Versace 50.5, Paco 40.5, Lancôme 51; **honest pends** (sephora carries only flankers): Libre, Mon Paris, Born In Roma, Mugler Alien, Prada Luna Rossa, + the Dior×3/MarcJacobs/V&R sephora-coverage gap
- [x] **prod-verified** (cached compare, no nocache): Oud Wood **77.0** + Black Orchid **55.5** via `zyte_render_bhd` cached=True — corrected genuine luxury prices LIVE in prod (served from shared cache via the already-deployed genuine method; no code deploy needed)
- [ ] **comm zero-regression gate** (branch-only-NEW == []) — RE-RUNNING (first run's extraction was buggy); + smoke20 vs `54b603e8` (needs prod Serper = railway login) before committing the (live-path-dormant) code to main

### KEY OUTCOME — genuine luxury BHD prices are LIVE + no-fab-correct
The hardening's net effect: the old loose matcher had cached **flankers** (Black Opium "Over Red", Good Girl/Born-In-Roma/Libre/Mon-Paris variants) and the **wrong concentration** (Oud Wood/Black Orchid Parfum). The hardened matcher flushed all of these → correct prices or honest pends. **Trade-off: correctness over coverage** (more luxury pends now; the lever for higher coverage is MORE walled sources, not matcher tuning).

### Size blind spot (documented follow-up, not no-fab)
The Zyte matcher strips size from identity, so among same-concentration listings it picks sephora's most-relevant which may be a non-standard size (Black Opium 85 may be 150ml). Right product + right concentration; size is reconciled downstream at compare-time. A size-aware Zyte tier is a future enhancement.

### Deferred (documented, not built)
- name-only search-variant fallback (#4) — probe showed it doesn't help Dior/the tested set; doubles Zyte calls (budget); revisit with more budget
- full api_budget_service Zyte metering (#3) — off-clock + manually bounded; kill-switch covers the acute risk
- per-brand canonical-concentration map (#6) — Acqua di Gio EDT vs EDP "which legit variant"; verify empirically on re-seed

## Step 4 — Mobile-app comparison (ONLY after 1–3 verified)
- Fresh compares on the iPhone across electronics / fragrance / supplements / makeup;
  inspect the REAL result content (prices/specs/reviews/images/scoring) — not a glance.
- Decide whether to build the full Zyte render-tier bundle (off-clock cron + more walled sites).

## Gates before any deploy
- comm zero-regression (`branch-only-NEW == []`)
- smoke20 vs baseline `54b603e8` (winner ≥ 0.50, factual held)
