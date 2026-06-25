# BH Source-Intelligence bundle — pre-merge REVIEW PACKET (for Codex / Ahmed)

Branch is **branch-ready, NOT merged, NOT deployed**. Comm-gate green. Cron stays OFF.

## 1. Branch + exact commit range
- **Branch:** `feature/bh-source-intelligence`
- **Range:** `fb8696c..123edaf` (11 commits). Codex review surface = the prod code:
  `git diff fb8696c..123edaf -- app/services scripts`
- Commits: `28a215e` design-doc, `d376d6e` plan-doc, `9fec6dd` WS-1 schema+registry, `87aa10c` contract-doc, `ef0f99d` WS-2 discovery, `b75c424` WS-3a/3b fetchers, `8c2794d` WS-3d hook, `5d2ead2` WS-3c boutiqaat, `570bf68` WS-3 bolo no-fab gate-fix, `c064a37` WS-4 sephora.me, `123edaf` WS-5 harness.
- **Prod code touched (6 files, +1264/-13):** `price_service.py` (+500: the 3 fetchers + parsers), `source_router.py` (+94: schema + registry), `structured_comparison_service.py` (+197: prefetch hook + Akamai markers), `scrapedo_service.py` (+10), NEW `sitemap_discovery_service.py` (298), NEW `scripts/cron_index_sitemaps.py` (178). Plus new test files + slim HTML fixtures + the out-of-band `.qa-bias-rerun/_sephora_provider_test.py`.

## 2. Schema change + rollback / backward-compat
- **NO DB migration.** The "schema change" is the `Source` **frozen dataclass** (`source_router.py:19`) gaining 8 NEW fields — `locale_paths, subdomain_patterns, currency, discovery_query_templates, mechanism, pdp_url_pattern, sample_url, status` — **ALL default empty/()** (frozen-safe bare `()` tuples, NO mutable default). Every existing positional/kwarg `Source(...)` row is byte-unchanged (pinned: `test_source_descriptor_fields`, Wave-1 managed audit confirmed all 42 existing rows construct identically).
- **Registry DATA changes (3 rows):** `bolo.bh` + `nasserpharmacy.com` flipped OFF `is_render_only` (+ `mechanism` set); `sephora.bh` domain literal → `sephora.me` (canonical BH, `requires_super` retained); `boutiqaat.com` flipped OFF render-only/super → `mechanism="sitemap"` (after the Wave-3c live re-verify GO).
- **Backward-compat:** additive selectors `get_jsonapi_sources_for_category` / `get_sitemap_sources_for_category`; no existing signature changed; `should_negative_cache` gained ONE additive exempt branch (`source_method=="sitemap_no_match"`).
- **Rollback:** revert the merge → `main` back to `fb8696c` → redeploy (~90s). **No DB/state to unwind.** Per-source rollback = a 1-line registry-row edit (below, §8).

## 3. Adapter list + regional-storefront handling
| Source | Function | Mechanism | source_method | Discovery |
|---|---|---|---|---|
| **nasserpharmacy.com** | `fetch_nasser_price` | json_api | `local_bhd` | own `/v1/filterSearchs` search API (single GET, static guest header const) — self-contained |
| **bolo.bh** | `fetch_bolo_price` | sitemap | `page_scrape_jsonld` | sitemap index → curl PDP → `_bolo_jsonld_main_price` (@graph offer, numbers+variant+word-overlap bound; Nuxt fallback ONLY when no JSON-LD product) |
| **boutiqaat.com** | `fetch_boutiqaat_price` | sitemap | `page_scrape_jsonld` | sitemap index → curl PDP → JSON-LD |
| **sephora.me /bh-en** | — (NO price adapter) | provider | — | Akamai-walled; provider-test candidate; `requires_super` → filtered out when `SCRAPEDO_SUPER` OFF (byte-identical OFF-state to the old sephora.bh) |

The **regional-storefront-alias descriptor** (the generalization Ahmed specified): `locale_paths` (`/bh-en` etc.), `subdomain_patterns`, `currency`, `discovery_query_templates`, `pdp_url_pattern`, `sample_url`, `status` — discovery/classification metadata per source. sephora.me is the canonical correction (sephora.bh was unverified + 301s).

## 4. LIVE immediately vs behind the sitemap-index cron
- **LIVE on deploy (no activation):** **nasserpharmacy.com** — genuine `local_bhd` on a COLD pull; fires a speculative authenticated GET per in-category compare (skincare/makeup/haircare/supplements/fragrances), parallel in the FREE prefetch slot, **cancelled on a Tier-1 short-circuit**, graceful `None` on 401/rate-limit. AND the registry render-only corrections (route bolo/nasser to curl-tier, not render).
- **BEHIND `ENABLE_SITEMAP_INDEX` (default OFF → dormant on deploy):** **bolo.bh + boutiqaat.com** — `resolve_pdp_via_sitemap` is a Redis read that returns `None` until the off-clock cron builds the index → `fetch_* → None → honest pending` (NO wrong data, graceful). So **shipping with the cron OFF adds NO bolo/boutiqaat genuine prices yet and carries no risk** (they're inert until you flip the cron).
- **sephora.me:** NO price path; gated OFF under `SCRAPEDO_SUPER` OFF.

## 5. Feature flags / env vars added or changed
- **NEW:** `ENABLE_SITEMAP_INDEX` (default OFF, fail-CLOSED). Gates ONLY the off-clock cron `scripts/cron_index_sitemaps.py`; **nothing in the request path reads it.** The cron is **NOT registered on Railway** (your activation).
- **NO existing env var changed.** `SCRAPEDO_SUPER` stays OFF (reverted this session, `08192be7`).
- The adapters ride the EXISTING `ENABLE_PAGE_SCRAPE` (prod=true) — no new gate for them.
- nasser static guest header = a module CONST in `price_service` (NOT an env var) — rotates on nasser's FE redeploy (the one live-credential risk; 401 → graceful None).
- Zyte: `ZYTE_API_KEY` read from LOCAL `.env` by the harness ONLY (NOT Railway, NOT prod code).

## 6. Tests run + smoke/eval results
- **Per-wave (TDD, mocked, no network):** WS-1 131 targeted + 918 broad; WS-2 12 + 51 negative-cache; WS-3 (23 fetchers + 6 hook + 8 boutiqaat + 42 gate-fix); WS-4 58; WS-5 46. Each adapter ALSO **live verify-or-omit**: nasser 13.341/8.882, bolo 24.89/8.16, boutiqaat 50.43/43.05/10.46 BHD.
- **Ship gate — free-unit `comm` zero-regression:** branch **49 failed / 7654 passed** vs main-base `fb8696c` **49 failed / 7572 passed** → **`branch-only-NEW == []`** (+82 new passing tests; the 49 are pre-existing identical — 35 `test_value_math` RED-by-design stubs + 2 `test_personalization_bundle_c` + 1 frontend grep + network "free" tests).
- **smoke20 / fresh-nocache genuine-share: NOT YET RUN** — `eval_runner` is a prod-HTTP harness → POST-deploy only (can't measure un-deployed branch code). Commands in §7.
- **Provider experiment RAN → inconclusive:** all Scrape.do calls 401 `"Monthly request limit exceeded"` (Scrape.do quota exhausted; plain=200 so token valid). Did NOT reach Akamai. Ops finding, not a code finding.

## 7. Post-deploy verification commands
```bash
# (a) smoke20 regression (read axis metrics MANUALLY; the auto "GATE FAIL" is the baseline-fetch tooling false-fail)
source .env && python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8 --concurrency 1
# accept: winner >= 0.50, factual 1.0 HELD, specs ~0.95 cold-noise

# (b) nasser genuine-share confirm (THE immediate win — expect source_method=local_bhd, retailer=Nasser, NOT converted_usd)
curl -s "https://web-production-58776.up.railway.app/api/v1/text/compare?q=CeraVe+Foaming+Cleanser+vs+Cetaphil+Gentle+Skin+Cleanser&nocache=true" \
  | python -c "import json,sys; d=json.load(sys.stdin); [print(p['name'], p['price'].get('source_method'), p['price'].get('retailer')) for p in d['products']]"

# (c) bolo/boutiqaat COLD (cron OFF) → expect pending, NOT genuine (correct, inert until the cron)

# (d) nasser token liveness (401 => re-scrape main.*.js)
python .qa-bh-sourcing/_verify_nasser.py

# (e) registry sanity
python -c "from app.services.source_router import get_jsonapi_sources_for_category as j, get_sitemap_sources_for_category as s; print('jsonapi/skincare', [x.domain for x in j('skincare')]); print('sitemap/makeup', [x.domain for x in s('makeup')])"
```

## 8. Rollback if a source returns WRONG prices
- **Per-source (fastest, ~90s):** flip the offending registry row's `mechanism` back + `is_render_only=True` (1-line `source_router.py` edit) → it drops out of `get_jsonapi/get_sitemap_sources_for_category` → no longer queried → redeploy. (No data loss; it just stops contributing.)
- **Kill ALL curl-adapters at once:** `ENABLE_PAGE_SCRAPE=false` on Railway (broad — also disables the pre-existing page-scrape tier).
- **Full bundle:** revert the merge commit → `main` to `fb8696c` → redeploy. No DB/state.
- **In-place defenses already shipped (a wrong price must beat ALL of these):** `is_price_showable` re-gates every adapter price (sample/decant/implausible-high/low floors); the bolo no-fab wrong-product guard (`_bolo_has_jsonld_product` + word-overlap, `570bf68`); per-adapter `strict_title_match`/`numbers_match`/`variant_mismatch`/word-overlap binding; `sitemap_no_match → None` (no fabrication, exempt from 30d negcache so a refresh can correct it).
- **Monitoring:** `/admin/costs` per-`source_method` bucket; `metadata.source_trace`; a fresh-`nocache` spot-check per source.

## Reviewer focus areas (where to scrutinize)
1. **No-fab adapter parsing** — can any adapter attribute a WRONG product's price? (the bolo gate-fix `570bf68` is the precedent; check nasser's `_match_nasser_product` which intentionally drops `is_accessory` — see commit msg — and boutiqaat's JSON-LD bind).
2. **Prefetch hook** (`scs` ~:4173) — the per-request speculative nasser GET, cancellation/no-orphan, and the **`not is_supplement` un-gate** (supplements must reach bolo/nasser; a narrow residual: a supplement detected only via `is_supplement_query` on `category in (other,None)` does NOT reach them — the `category=="supplements"` path does).
3. **Schema backward-compat** — all existing `Source(...)` rows byte-unchanged.
4. **Off-clock-only** sitemap discovery — `build_sitemap_index` must NEVER be on the 15s request clock (grep: only `cron_index_sitemaps.py` calls it; `resolve_pdp_via_sitemap` is Redis-read-only).
5. **`should_negative_cache`** exemption (additive, `sitemap_no_match`).

**After review, if clean:** ship backend-only with the cron OFF first (nasser genuine immediately; bolo/boutiqaat inert until a SEPARATE cron-activation decision). The Scrape.do quota exhaustion (ops) + the sephora provider verdict (Zyte/reset) are separate, non-blocking.
