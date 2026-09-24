"""docs_patch_s67.py <docs-worktree> : apply the session-67 documentation edits.
Reads rw04_facts.json (next to this script) for the last group's final facts and the
session-67 state draft, patches CLAUDE.md + docs/CONTEXT_SESSION_LOG.md (CRLF preserved)
and writes docs/investigations/2026-09-24-session-67-state.md. Idempotent: refuses to
apply an edit whose marker is already present."""
import json, pathlib, sys

WT = pathlib.Path(sys.argv[1])
SP = pathlib.Path(__file__).resolve().parent
F = json.load(open(SP / "rw04_facts.json", encoding="utf-8"))


def load(rel):
    p = WT / rel
    raw = p.read_bytes()
    return p, raw.decode("utf-8").replace("\r\n", "\n"), (b"\r\n" in raw)


def save(p, text, crlf):
    p.write_bytes(text.replace("\n", "\r\n").encode("utf-8") if crlf else text.encode("utf-8"))


def replace_once(text, old, new, label):
    n = text.count(old)
    assert n == 1, f"{label}: expected 1 occurrence, found {n}"
    return text.replace(old, new, 1)


# ---------------------------------------------------------------- CLAUDE.md
p, t, crlf = load("CLAUDE.md")
assert "SESSION 67 flags" not in t, "CLAUDE.md already patched"

# (b) W1-4 row correction
t = replace_once(
    t,
    "**INERT until the client sends it:** the refresh token in the logout body is a CLIENT change that reaches devices only with the next `eas update`, so flag ON is a no-op for every build now on phones — which is the whole reason the flag exists.",
    "**INERT until the client sends it:** the refresh token in the logout body is a CLIENT change that reaches devices only with the next `eas update`, so flag ON is a no-op for every build now on phones — which is the whole reason the flag exists. **CORRECTED by R-AUTH (#194, 2026-09-24): NO LONGER INERT.** With the flag ON the backend revokes by the ACCESS token — `admin.sign_out(access_token, \"local\")` through `run_db` regardless of the refresh token — and an EXPIRED bearer with a `refresh_token` body refreshes once (`set_session`, rotates) then signs out local and blacklists, budgeted at 10/minute per limiter key (its own bucket, checked after the expiry and token checks). With `ENABLE_PROXY_AWARE_RATELIMIT` ON that key is the caller-chosen leftmost `X-Forwarded-For` (the exposure `/auth/refresh` already has) — follow-up W1-9e BEFORE flipping this flag on a proxy-aware deployment. Unflagged alongside it: refresh failures are classified by exception TYPE (W1-4b), server-side Supabase clients never auto-refresh (`auto_refresh_token=False, persist_session=False`, W1-4c), and lockout arming is atomic with a TTL re-arm (W1-9b).",
    "W1-4 row",
)

# (c) W0-4 row: the false heartbeat/iHerb sentences
t = replace_once(
    t,
    "a 50 ms heartbeat ticked **0** times through a 0.31 s parse. **Effect ON:** the soup is built once and threaded into all three JSON-LD passes, and the three async sites `await asyncio.to_thread(...)`. Flag OFF: four soups, inline call, byte-identical. `price_service.py:15425` (`fetch_iherb_price`) already parses inside a `run_in_executor` lambda and is deliberately untouched.",
    "the loop was frozen for the whole parse (measured by R-W04: 300–602 ms per inline parse at the six sites below; a 50 ms heartbeat ticked **0** times). **Effect ON (as amended by R-W04, "
    + F["pr_ref"]
    + "):** the soup is built once and threaded into all three JSON-LD passes; EVERY pure-sync parse site — the three original ones plus `fetch_iherb_price`, `fetch_bolo_price`, `fetch_boutiqaat_price`, `_try_pharmacy_urls`, `url_extraction_service.extract_with_ai` and `StructuredComparisonService._fetch_page_price` (which parsed INLINE on the loop; the earlier sentence that iHerb \"already parses inside a run_in_executor lambda\" was FALSE) — runs as ONE job on a dedicated, bounded `price-parse` `ThreadPoolExecutor` (`PRICE_PARSE_MAX_WORKERS`, default 4, clamped 1..16, unparsable/non-finite → 4, read ONCE when the pool is built) behind a per-event-loop `asyncio.Semaphore` of the same size acquired BEFORE submit (queued parses wait in asyncio, not in the executor), entered through `contextvars.copy_context().run` so the resolved-category ContextVar reaches the worker; `curl_fetch_html` and the firecrawl/scrapedo render legs hand at most `PRICE_FETCH_MAX_BYTES` = 3,000,000 chars to the parse (mirroring `curl_fetch_html_same_site`; the provider-attempt `html_kb` telemetry still reports the raw body). A source-level AST guard keeps the inline-parse allowlist EMPTY. Flag OFF: four soups, inline call, the whole body, byte-identical (corpus OFF OVERALL `9504e5a9…`, results `a1b3460c…` equal to a same-env `origin/main` run; ON `--compare` OFF: 0 of 1656 records differ; 11 corpus records exceed 3,000,000 chars and none moves under the cap). **Residual (measured):** offloaded parses of the largest (3.9–4.1 MB) pages still cost the loop 35–143 ms single and 171–534 ms with six at once (six median pages 142–174 ms) against 1,089 ms inline — the pool bounds it, it does not remove it. **Stated limit:** under the flag the 3 MB cap also applies to `_lazy_bh_pdp_backfill`'s regex scan of a curled search page (an href past 3,000,000 chars is no longer found — W0-4e). Harness: `scripts/verify_flag_byte_identity.py --flags-on <flags>` (restores the prior env, incl. unset) and `--compare <other-results.json>` (results-array sha equality + the first differing records; exit 1 on mismatch).",
    "W0-4 row",
)

# (d) activation step (2)
t = replace_once(
    t,
    "(2) `ENABLE_PRICE_PARSE_OFFLOAD` — pure latency/CPU placement, no result change (the corpus gate proves it).",
    "(2) `ENABLE_PRICE_PARSE_OFFLOAD` — pure latency/CPU placement, no result change (the corpus gate proves it, ON vs OFF 0/1656 with the 3 MB cap in place); size `PRICE_PARSE_MAX_WORKERS` (default 4) for the box and watch the price-parse pool's queue depth together with `/health` `loop_lag_ms` / `loop_lag_max_60s_ms` — the measured residual is 35–143 ms per large page even when offloaded (R-W04).",
    "W0 activation step 2",
)

# (e) the CORRECTION paragraph: mark the retro PRs merged and fix the apply order
t = replace_once(
    t,
    "The retro fix (R-MAIN, unmerged at the close) swaps in the ASGI middleware so those 3 routes 429 with the envelope + `Retry-After` instead of slowapi's bare body; whether router routes should be limited at all is an open orchestrator ruling. Two more corrections land with the retro PRs: the W1-4 row's \"INERT until the client sends it\" is only true until R-AUTH makes the backend call `admin.sign_out(access_token, \"local\")` regardless of the refresh token; the migration apply order becomes `035 -> 036 -> 037 -> 040` with 037 no longer depending on 035/036 (R-MIG rewrites 037, adds 040, and 036 needs re-running 037 after a late 036).",
    "The retro fix (R-MAIN, **MERGED #187 2026-09-24**) swaps in `SlowAPIASGIMiddleware` so those 3 routes 429 with the envelope + `Retry-After` instead of slowapi's bare body; on the pinned slowapi that middleware re-sends `http.response.start` before EVERY body chunk, so every route the default can reach must stay single-chunk (pinned: `/health`, `/`, `/favicon.ico`, + the four docs routes off Railway) — widening the default to router routes or adding an undecorated multi-chunk app-level route is follow-up W1-9d, not a config flip. The two further corrections LANDED: the W1-4 row above is corrected in place (R-AUTH #194); the migration apply order is `037 any time (it depends on nothing unapplied: statement 4 is guarded by to_regprocedure); 036 when its flag is readied — re-run the idempotent 037 after a late 036; 040 any time (run its header census first); 038 = W3-16; 039 reserved for the M13-29 RLS migration` (R-MIG #189: 037 rewritten, 040 added, 036 revokes anon; the old `035 -> 036 -> 037` prerequisite is withdrawn).",
    "CORRECTION paragraph",
)

# (f) the consolidated-review correction that was itself wrong
t = replace_once(
    t,
    "`cleanup_expired_ratings` (named in `CR-SECURITY-01`) **does not exist** anywhere in `migrations/` or `app/` — the actual third unguarded `SECURITY DEFINER` function is `resolve_referral_code`,",
    "`cleanup_expired_ratings` (named in `CR-SECURITY-01`) **does not exist** anywhere in `migrations/` or `app/` — **CORRECTED 2026-09-24 (R-MIG #189): it EXISTS LIVE, created out of band (the 2026-09-06 live review recorded it; an anon-key GET on `/rpc/cleanup_expired_ratings` returned SQLSTATE 25006, i.e. anon passed EXECUTE); migration 040 revokes it BY NAME from PUBLIC/anon/authenticated and its header carries the catalog census to run first** — the third unguarded function this repo can SEE is `resolve_referral_code`,",
    "consolidated-review correction",
)

# (a) SESSION 67 flags block, inserted right after the SESSION 66 flags block (before the Tests heading)
flags_block = (
    "\n**SESSION 67 flags (2026-09-24; every row default OFF, read PER CALL via `os.getenv`, Railway READ via the CLI — " + F["prod_state_short"] + "; merged #192 W4-2 → " + F["pr_ref"] + " R-W04 alongside the retro wave).**\n"
    "- `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (W4-2, `PO-RECORDED-MEASURED-03`, `app/services/price_service.py::shopping_discovery_url_split_enabled`, PR #192) — **TRUE only when `ENABLE_SHOPPING_CURRENCY_TRUTH` is also true (ruling R1)**, both read per call. **Effect ON:** the Serper-shopping rung never puts a SEARCH link in `price[\"url\"]` — a listing `link` (rung 1) or the synthesized `build_retailer_url` fallback (rung 2) rides in the PRIVATE key `_discovery_url` with `url: None`, a real PDP link is untouched (rung 3); the stash mirror `_seed_shortcircuit_candidates` applies the same splitter; the tier-7 `converted_fallback` backfill never re-mints a url for a row carrying the key (`_discovery_url_of` reads the key with NO flag read, ruling R3, so a mid-request rollback cannot re-mint one); `public_price_view` and `GET /api/v1/text/prices/{product}` strip ONLY `_discovery_url` under the exact gate; one `[SHOPPING_DISCOVERY_URL] split url->_discovery_url host= reason=` INFO line for `best`. **Flag OFF:** byte-identical to `6ab9d7ea` (corpus base → head → base2, record by record; the harness never enters the shopping rung — stated). **Consequence:** rows from the 9 non-listing-template retailers (amazon, amazon.ae, amazon.sa, target, newegg, adorama, apple, ebay, aliexpress) lose their 24 h/7 d cache (a fabricated url must never be cached); with `ENABLE_EXACT_PRICE_GATE=false` a discovery-only row becomes cacheable/selectable (pinned as current behaviour). **Activation order for the shopping tier:** W4-1 → W4-2 → W4-3; `ENABLE_REGION_CURRENCY_GUARD` LAST. **THE FLIP IS GATED ON AHMED'S PRODUCT CALL** with the \"(converted from USD)\" rendering in front of him (W4-1 ruling R5). Follow-ups: `PO-RECORDED-MEASURED-03b` (amazon.ae/amazon.sa collide to amazon.com in `RETAILER_SEARCH_URLS`), 03c (`google.com/shopping/product/<id>` links are not caught by `_is_listing_url`), the pre-existing `_cached` leak on `/text/prices`.\n"
    "- `ENABLE_CAMERA_FAILURE_ENVELOPE` (R-METER, W2-1b, `app/api/image_routes.py::camera_failure_envelope_enabled`, PR #195) — **Effect ON:** an UNSUCCESSFUL camera comparison (`compare_from_text` returned `success: False` — TIMEOUT / INSUFFICIENT_DATA / LLM_UNAVAILABLE / CONTENT_UNAVAILABLE or the code-less generic branch) is served as the `comparison_failed` envelope exit 6 already ships (the 97b5f15 client's fall-back-to-text branch handles it) carrying the result's own code (`INTERNAL_ERROR` for a code-less one). **Flag OFF:** today's `action: \"comparison\"` body, except that a code-less result's `error` (the service's `str(e)`, measured carrying an OpenAI key tail) is the constant `comparison unavailable` — UNFLAGGED (M13-26 class). **The no-bill half lives inside the EXISTING `ENABLE_PAID_ROUTE_METERING`:** an unsuccessful result is a NON-delivery — reserved credit refunded, anon credit refunded once (W2-1d wired `refund_anon_comparison_credit` on the six non-delivery exits + this one), no `record_lifetime_comparison`, no history row, `log_search success=False` — pinned in the both-flags-ON deploy state. **FLIP BOTH TOGETHER:** envelope ON + metering OFF still logs success and writes a history attempt (pinned, by design). Unflagged alongside: `compare_from_urls` never delivers a verdict carrying a non-empty `error` (generate_comparison's except-branch used to ship `success: True` with a fabricated `winner_index 0` and the raw exception text) — it returns `LLM_UNAVAILABLE` and `/url/compare` ships **503** with the constant message through the text route's mapping (a coded failure only; the code-less `<2 products` exit keeps its bare-string 400 — W4-9's codeless allowlist would redact it). Recorded for #128, not built: `/url/compare` has NO anonymous gate; the anon credit on `/image/identify` is debited BEFORE the five image-validation 400s.\n"
    + F["w04_flag_row"]
    + "\n"
)
t = replace_once(t, "\n## Tests\n", flags_block + "\n## Tests\n", "SESSION 67 flags insert")

# (g) Active runtime (SESSION 67) block before the SESSION 66 one
active = (
    "## Active runtime (SESSION 67 — the retro-fix wave and every open PR from the session-66 close MERGED; " + F["pr_total"] + " PRs; main `" + F["main_sha"] + "`, 2026-09-24)\n\n"
    "**STATUS 2026-09-24 " + F["close_time"] + " — main `" + F["main_sha"] + "`.** The box recovered (spawns instant; the session-66 8–82 s pathology did not recur). Merged in order: #182 docs, #181 (#44 rescue), #180 (#36 rescue), #177 W4-3, #179 W4-4, #178 W4-9, #187 R-MAIN, #190 R-CLIENT, #188 R-BREAKER, #189 R-MIG, #191 R-W0, #192 W4-2, #193 R-W18, #194 R-AUTH, #195 R-METER" + F["merged_tail"] + ". #36 and #44 closed as superseded. Every retro branch the close had pushed as UNVERIFIED wip went through a FRESH adversary on its exact committed bytes → a fix round where anything survived → a re-adversary → a Fable diff review → ONE squashed commit → a rebase onto current main → the unit set re-run in CI (alphabetical) order → CI on the rebased sha (verified by check-run timestamps) → merge. The full ledger, every verdict, ruling, PR body, script and harvested agent report are in `docs/investigations/2026-09-24-session-67-state.md` (+ its `state/` folder). The block below carries only what CLAUDE.md must know.\n"
    "- **PRODUCTION DOWN (measured 2026-09-24 ~15:00 local via the Railway CLI):** " + F["prod_state"] + "\n"
    "- **Four latent hazards the CI-red PRs exposed are issues, not fixed in code:** #183 (`tests/test_hotfix_shopping_query_clean.py` reloads `serper_service` with a fake key and never restores the module global), #184 (every autouse socket guard misses `curl_cffi` — native libcurl; the W4-9 quota-outage tests fetched three Bahraini Shopify stores and noon FOR REAL, in CI too; the repo-wide netguard 04c must patch `curl_cffi.requests.Session.request` / `AsyncSession.request` / `Curl.perform` / `AsyncCurl.add_handle`), #185 (`tests/test_platform_router.py` deletes `price_service` from `sys.modules` and never restores it, orphaning every by-name binding — `test_shopify_discovery_l13::test_fetch_uses_catalog_and_matches` passes in CI only via the LIVE store), #186 (W4-3's unit file run before W4-4's breaks three flag-ON nodes; CI's alphabetical order hides it). Until 04c lands: every new test file carries its own guard AND the unit set is run in CI order.\n"
    "- **What changed for callers with every flag OFF (unflagged by ruling, each a defect with no legitimate reader):** R-MAIN — sampled Sentry performance transactions are scrubbed like error events (`before_send_transaction`, `X-Admin-Key`/`Authorization`/`Cookie`/PII); a raw byte ≥ 0x80 in an `/admin/*` Basic credential is a 401, never a 500; `/health` gains `loop_lag_max_60s_ms`. R-AUTH — refresh failures classified by TYPE; server Supabase clients never auto-refresh; lockout arming atomic with a TTL re-arm. R-BREAKER (inside its flag) — a cancelled dispatch never trips the OpenAI breaker; every half-open probe ends its slot. R-W18 — adapter drops are grep-stable INFO lines (`[ADAPTER DROP] fanout:<kind>:<domain>: FETCH-FAIL|ERROR <Type>`, `[FANOUT] wave=… completed= failed= cancelled= elapsed=`, `CONSUME-BOUND after`, `SLOW-MISS after`), exception text scrubbed by `_safe_exc`; no return value moves. R-METER — a code-less unsuccessful camera result's `error` is a constant; `/url/compare` never ships a fabricated verdict (503 `LLM_UNAVAILABLE`). W4-9 — every `str(e)` on the text compare paths is the INTERNAL_ERROR envelope. R-CLIENT (OTA-gated) — logout awaits an in-flight refresh (5 s bound), refreshes an expired JWT once, and hands the rotated pair only to the logout that owns the session epoch. R-MIG — NO production change (unapplied files).\n"
    "- **Mobile OTA (the lever for the whole W3 lane; status: " + F["ota_line"] + "):** the W3 client halves AND R-CLIENT's W1-4d logout are main-only until `eas update --branch preview --clear-cache` from main ≥ `" + F["main_sha"] + "`; `ENABLE_PASSWORD_RESET_DEEP_LINK`, `ENABLE_CONSENT_REQUIRED` and `ENABLE_LOGOUT_UPSTREAM_REVOCATION` must not flip before it (the last one also needs W1-9e on a proxy-aware deployment).\n"
    "- **Merge-time lessons (binding for the next lane):** (1) a killed adversary leaves mutants — the session-66 close commit of R-MAIN carried a 59-slot-ring mutant because the close re-check skipped the PARTIAL groups; every report carries the final sha256 of every file it wrote and the next adversary re-runs the unit files FIRST; (2) retro groups touching routes are REBASED before their last adversary (R-METER's round 3 caught main's W4-9 codeless allowlist redacting the `/url/compare` `<2 products` body); (3) a unit's CI-order set includes every file that PINS the functions it touches (R-AUTH's W1-4c contradicted two R-W0 pins that only CI ran); (4) workflow scripts are pure ASCII/LF written with the Write tool — Git Bash heredocs mangle backslash-letter sequences and Windows text-mode writes CRLF, both of which the Workflow tool rejects; (5) agents keep copying `.env` into scratch dirs — sweep `find <scratchpad> -name .env` after every workflow.\n"
    "- **Ahmed's list (dependency order):** **select a Railway plan, then redeploy `web` and `qaren-landing` (the trial expired 2026-09-21; nothing merged since #162 has ever run in prod)**; rotate the eight leaked keys (+ the R-W0 harness incident), then `ADMIN_API_KEY`; `ENABLE_BRIGHTDATA_BUDGET_GATE=true` is DONE on both services (takes effect on the first deployment after the plan); " + F["ota_line"] + "; the two decision briefs (`DECISIONS_AHMED.md`) and the migration apply pack (`APPLY_PACK_AHMED.md` §A–§E) are in the state folder; migrations 038 → (037 and 040 any time, 040's header census first) → 039; `EXPO_TOKEN`; the Supabase Redirect-URL entry `qaren://reset-password`; W3-7 icons + `eas build`; the legal review; the #101 call (W4-6b) and the W4-2 \"(converted from USD)\" call; `railway login`; keep the Surfshark/NZXT exclusions.\n"
    "- **Next:** " + F["next_1"] + " the remaining W4 specs (6a, 7, 8, 11, 12, 13, 14; 6b waits on #101) through spec → adversarial spec review → red → gate → green; skill Step 2 tooling; the config-audit fixes as a docs/config PR; the Step 6 structured review at the milestone end; the end-of-session redaction re-run.\n\n"
)
t = replace_once(t, "## Active runtime (SESSION 66 — ONE session, both lanes:", active + "## Active runtime (SESSION 66 — ONE session, both lanes:", "Active runtime insert")
save(p, t, crlf)
print("CLAUDE.md patched")

# ---------------------------------------------------------------- session log
p, t, crlf = load("docs/CONTEXT_SESSION_LOG.md")
assert "# SESSION 67 " not in t, "session log already patched"
entry = (
    "# SESSION 67 — the retro-fix wave and every open PR from the session-66 close merged: " + F["pr_total"] + " PRs, four latent test hazards filed as issues (2026-09-24)\n\n"
    "**Production, measured 2026-09-24 ~15:00 local via the Railway CLI:** " + F["prod_state"] + " OTA: " + F["ota_line"] + "\n\n"
    "**Merged (main `" + F["main_sha"] + "`), in order:** #182 docs (session-66 close state), #181 the PR #44 rescue (`OPENAI_BASE_URL` fails CLOSED), #180 the PR #36 rescue (Gents/Ladies + strict gender wins), #177 W4-3 `ENABLE_PRESCORING_SHOWABLE_GUARD`, #179 W4-4 `ENABLE_HONEST_PARTIAL_SCORING`, #178 W4-9 `str(e)` envelope, #187 R-MAIN, #190 R-CLIENT, #188 R-BREAKER, #189 R-MIG, #191 R-W0, #192 W4-2 `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`, #193 R-W18, #194 R-AUTH, #195 R-METER" + F["merged_tail"] + ". #36 and #44 closed as superseded. Every flag default OFF, nothing flipped, Railway never read.\n"
    "**Process that held:** each session-66 UNVERIFIED wip branch → fresh Opus 5.5 adversary on the exact committed bytes → fix round (blocking/major/prove-nothing rows) → re-adversary (up to four rounds for R-METER) → Fable diff review → one squashed commit → rebase onto current main → unit set in CI order → CI on the rebased sha → merge. Findings the wave surfaced: a 59-slot-ring MUTANT in the session-66 close commit of R-MAIN (the close skipped the PARTIAL groups' re-run); an unauthenticated upstream-refresh amplifier on R-AUTH's flag-ON expired-bearer path (now budgeted 10/min); a cross-session logout handoff in R-CLIENT (now epoch-keyed); R-MIG's 040 `proname` filter unpinned (engine-verified mutants now killed); R-W18's per-scraper drop lines could never fire (moved to where the fetch layer swallows); R-METER's rebase-composition defect against W4-9's codeless allowlist; W4-2's private `_discovery_url` reaching the wire on `GET /text/prices` (stripped).\n"
    "**CI-red PRs → issues:** #183 Serper reload leak, #184 curl_cffi bypasses every socket guard (real Shopify/noon fetches from CI), #185 `sys.modules` deletion orphans by-name bindings (one discovery test passes only via the live store), #186 W4-3-before-W4-4 order dependence. W4-3's three pins moved to W4-10's deduped labels; W4-9's quota-outage tests stub every reachable `price_service` module dict.\n"
    "**Box / tooling:** spawns instant all session (the 66 pathology gone); `gh` still unusable → `state/pr_rest.py` (create/status/watch/merge) + `ci_logs.py` (follows GitHub's Azure-blob redirect without the auth header); Workflow scripts must be ASCII/LF (Write tool; heredocs mangle backslash-letter sequences; text-mode writes CRLF); five `.env` copies agents left in scratch dirs were deleted and the rule added to every brief. Details: `docs/investigations/2026-09-24-session-67-state.md` (+ `state/`).\n\n---\n\n"
)
t = replace_once(t, "\n---\n\n# SESSION 66 — ", "\n---\n\n" + entry + "# SESSION 66 — ", "session log insert")
t = replace_once(
    t,
    "`cleanup_expired_ratings` (named in `CR-SECURITY-01`) does not exist anywhere; the actual third unguarded `SECURITY DEFINER` function is `resolve_referral_code`, deliberately granted to `anon` because signup needs it, so its fix differs in kind.",
    "`cleanup_expired_ratings` (named in `CR-SECURITY-01`) does not exist anywhere [CORRECTED 2026-09-24, R-MIG #189: it EXISTS LIVE, created out of band; migration 040 revokes it by name]; the actual third unguarded `SECURITY DEFINER` function the repo can see is `resolve_referral_code`, deliberately granted to `anon` because signup needs it, so its fix differs in kind.",
    "session log correction",
)
save(p, t, crlf)
print("session log patched")

# ---------------------------------------------------------------- state doc
draft = (SP / "session67_state_draft.md").read_text(encoding="utf-8")
for k, v in F["draft"].items():
    assert ("{{" + k + "}}") in draft, "placeholder missing: " + k
    draft = draft.replace("{{" + k + "}}", v)
assert "{{" not in draft, "unfilled placeholder remains"
out = WT / "docs/investigations/2026-09-24-session-67-state.md"
out.write_text(draft, encoding="utf-8", newline="\n")
print("state doc written:", out)
