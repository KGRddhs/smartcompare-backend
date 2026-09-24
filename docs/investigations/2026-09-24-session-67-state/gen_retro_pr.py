"""gen_retro_pr.py <KEY> : write prbody_<KEY>.md and msg_<KEY>.txt for a retro group from the
harvested fix pr_text plus the orchestrator's header (units, gates, verdict, follow-ups)."""
import json, sys, pathlib

KEY = sys.argv[1]
SP = pathlib.Path(__file__).resolve().parent
FIX = json.load(open(SP / f"retro_fix_r1_{KEY}.json", encoding="utf-8"))
ADV = json.load(open(SP / f"retro_adv_{KEY}_r1.json", encoding="utf-8"))

HEAD = {
 "R-BREAKER": dict(
  title="retro(llm): R-BREAKER - a cancelled dispatch never trips the OpenAI breaker; every half-open probe ends its slot",
  subject="retro(llm): W1-3a cancellation records no breaker failure, W1-3b every half-open probe records a total outcome",
  units="W1-3 (#147, merged in session 65 without review)",
  facts=("**Verdict:** adversary round 0 SOUND (5 minors, 3 prove-nothing rows) -> fix round (pins for the cancelled-probe outcome and the probe-only Exception arm; a teardown-class `except BaseException` release arm, probe-only) -> adversary round 1 **SOUND** (one equivalent mutant recorded, no test gap).\n\n"
         "**Gates:** unit files (`tests/test_retro_w1_3.py` + `tests/test_openai_breaker.py`) 79 nodes green on the pinned venv under a process-wide netguard in both flag states; comm gate over the 16-file set base == head; `ENABLE_LLM_PREFLIGHT_BREAKER` OFF byte-identical (pinned); every mutation from byte snapshots, sha-verified restores.\n\n"
         "**Stated limits / follow-ups (W1-3c, not this unit):** a dispatch admitted fail-open during an INCR blip carries probe=True and its release can reset the counter under a real in-flight probe (a second concurrent probe); a stale half_open memo routes a non-probe admission through is_circuit_closed so a 4xx wipes a standing CLOSED streak.\n"),
  msg=("Retro-fix group R-BREAKER for W1-3 (#147). Inside ENABLE_LLM_PREFLIGHT_BREAKER (default OFF, flag OFF byte-identical):\n"
       "- W1-3a (BLOCKING): a bare asyncio.CancelledError in guarded_llm_create records NO breaker failure (a sibling wall,\n  the hard cap, a disconnect or a shutdown is not an OpenAI health signal); three concurrent dispatches cancelled by\n  one outer wall leave the breaker CLOSED (pinned).\n"
       "- W1-3b: _openai_dispatch_admission returns (admitted, outcome_matters, probe); every admitted half-open probe\n  records a TOTAL outcome - a non-429 4xx is success-for-health (the server answered), any other exception, a\n  cancellation or a teardown BaseException releases the probe slot (openai_release_half_open_probe resets the\n  per-trip counter to 0 on a still-half_open blob), so a failing probe never wedges deny-all until the TTL.\n"
       "Tests: 79 nodes green both flag states; comm 16-file set base == head; adversary r1 SOUND."),
 ),
 "R-MIG": dict(
  title="retro(migrations): R-MIG - 037 self-contained (guarded statement 4, BEFORE checks, honest rollback), 036 revokes anon, new 040 revokes cleanup_expired_ratings by name",
  subject="retro(migrations): W1-2b/c/d - 037 no longer depends on 035/036, user_events BEFORE checks + honest rollback, 036 revokes anon, 040 revokes cleanup_expired_ratings by name",
  units="W1-2 migration 037 (#153, merged in session 65 without review)",
  facts=("**MERGING THIS CHANGES NOTHING IN PRODUCTION** - 036/037/040 stay unapplied files. Apply order becomes `037 any time; 036 when its flag is readied (re-run 037 after a late 036); 040 any time; 038 = W3-16 (consent columns); 039 reserved for the M13-29 RLS migration`.\n\n"
         "**Verdict:** adversary round 0 DEFECTIVE (major: 040's `proname` filter was unpinned - a mutant that revoked EVERY public function passed; two semantic mutants `PERFORM`/`pg_get_function_arguments` survived) -> fix round (source pins on the executed statement shape, the loop predicate, the 036 anon grant, the 037 header rule; docs lines corrected) -> adversary round 1 **SOUND** on a real engine (local throwaway PostgreSQL 18.1, Supabase-style default privileges): every round-0 mutant is killed.\n\n"
         "**Gates:** 103 source-level unit nodes green (`tests/test_retro_w1_2b.py`, `_2c.py`, `_2d.py`, `tests/test_migration_037_security_definer_grants.py`, `tests/test_migration_index_predicate_immutability.py`); comm gate over the 25-file migration set base == head; the fix changed only comments in 037's executable SQL.\n\n"
         "**Honest limits (adversary r1 minors, recorded, not blocking):** 040's `BEGIN;/COMMIT;` wrapper and the loop's WHERE are pinned only from below - `COMMIT->ROLLBACK`, an extra `AND p.pronargs = 0` or `AND false` conjunct survive the source pins (on the engine they leave anon EXECUTE standing with rc 0). The after-apply census in 040's header (the pg_proc/proacl query) is the real proof and MUST be run; a source test cannot replace it.\n\n"
         "**CLAUDE.md / docs corrections carried by the next docs PR:** the migration apply-order sentence; `docs/CONTEXT_SESSION_LOG.md:68` still says `cleanup_expired_ratings` does not exist anywhere (it exists LIVE, created out of band - 040 revokes it by name); `docs/investigations/2026-09-11-w3-remainder-state.md:126` is corrected in this PR.\n"),
  msg=("Retro-fix group R-MIG for W1-2 (#153). No production change (unapplied files).\n"
       "- W1-2b: new migrations/040_revoke_cleanup_expired_ratings.sql - an idempotent DO block that REVOKEs EXECUTE FROM\n  PUBLIC, anon, authenticated on every public function of that NAME (signature unknown to the repo; created out of\n  band, measured live in the 2026-09-06 review); header carries the catalog queries and the anon-executable\n  SECURITY DEFINER census to run first; the wrong 'does not exist' assert is replaced by a pin that 040 names it.\n"
       "- W1-2c: 037's header gains the user_events BEFORE checks (relrowsecurity + pg_policies with qual/with_check) and\n  the rule that any policy other than events_insert/events_select means CR-SECURITY-02 is NOT closed; the rollback\n  restores the recorded BEFORE value instead of blindly disabling RLS.\n"
       "- W1-2d: statement 4 is guarded by to_regprocedure('public.home_savings_aggregate(uuid)') so 037 no longer\n  depends on 035/036; 036's revoke names anon as well as PUBLIC (a stock Supabase explicit anon grant survives a\n  PUBLIC-only revoke, measured on PostgreSQL 18); apply order corrected in the docs it appears in.\n"
       "Tests: 103 source-level nodes green; engine-verified mutants killed; adversary r1 SOUND (2 recorded minors)."),
 ),
 "R-W0": dict(
  title="retro(net): R-W0 - the SSRF resolver memoises only confirmed negatives and genuinely slow resolves; the shared Supabase transport is HTTP/1.1",
  subject="retro(net): W0-1b memoise only EAI_NONAME/EAI_NODATA and started-and-ran timeouts, drop a stale negative when a zombie resolves public; W0-2b shared transport http2=False",
  units="W0-1 DNS memo + W0-2 shared transport (#135, merged in session 65 without review)",
  facts=("**Both flags stay default OFF** (`ENABLE_OFFLOOP_DNS_RESOLVE`, `ENABLE_SUPABASE_CLIENT_REUSE`); flag OFF is byte-identical to base (the M13/M14 construction pins re-run as mutations).\n\n"
         "**Verdict:** adversary round 0 SOUND (2 minors, 7 prove-nothing rows) -> fix round (an empty zombie answer no longer drops a negative; 9 of 11 surviving mutants folded into pins) -> adversary round 1 **SOUND** (2 minors recorded below, both stated limits).\n\n"
         "**Gates:** 71 unit nodes green through the process-wide guarded runner `.qa-retro/run_pytest.py` (third-party pre-import only, non-loopback socket guard) in both flag states; the 35-file comm set through the same runner with exactly the 5 accepted base failures (3 example.com SSRF nodes + the live-opt-in env test + the deselected cold `import app.main` node); every mutation from byte snapshots with sha-verified restores; the four `gaierror(-2)` stubs in the two existing offloop test files switched to `socket.EAI_NONAME` so they hold on Windows (11001) and Linux (-2).\n\n"
         "**W0-2b measurement (red phase):** on one shared HTTP/2 connection httpcore 1.0.9 couples every in-flight Supabase call and allocates h2 stream ids outside its write lock - ~4% of concurrent requests failed with NO hung call; 0 of 3,989 with `http2=False` (loopback TLS+ALPN). The keep-alive HTTP/1.1 pool keeps the CR-PERFORMANCE-03 shared SSLContext win; `max_connections` stays >= the run_db executor width.\n\n"
         "**Stated limits / follow-ups:** (1) the done-callback pops ANY `False` memo for the host, including a concurrent private-address negative another call wrote (ruling 3's single mechanism; the next call simply re-resolves) - follow-up W0-1d could key the memo entry by verdict kind; (2) the late re-check after a memo write is unpinned for a PRIVATE or EMPTY zombie answer in the deadline-to-write race window (the done-callback path IS pinned); W0-1c single-flight and the non-finite `SUPABASE_POSTGREST_TIMEOUT_SECONDS` knob stay open follow-ups.\n\n"
         "**HARNESS INCIDENT (already on the rotation list):** this group's red phase once imported `app.services.price_service` before conftest neutralised credentials, with no network guard - real OpenAI/Serper/Upstash calls in that alphabetical range cannot be ruled out; rule 9 (never import app.* before conftest, never run pytest without the process-wide guard) is now in every brief.\n"),
  msg=("Retro-fix group R-W0 for W0-1/W0-2 (#135). Both flags stay default OFF; flag OFF byte-identical (pinned).\n"
       "- W0-1b (inside ENABLE_OFFLOOP_DNS_RESOLVE): a gaierror is memoised as a negative only for EAI_NONAME / EAI_NODATA read\n  from the platform at call time (EAI_AGAIN, EAI_FAIL, errno None fail closed for this call only); a timeout is memoised\n  only when the resolve STARTED and ran >= 0.75 of the bound by the deadline; a done-callback drops a stale False memo\n  when a zombie resolve returns an allowed public address (never writes True - the DNS-rebinding window stays closed).\n"
       "- W0-2b (inside ENABLE_SUPABASE_CLIENT_REUSE): the shared httpx transport is built with http2=False (HTTP/1.1\n  keep-alive pool) so a hung PostgREST call cannot head-of-line-block unrelated requests; the OFF-path construction\n  of the anon and user clients is pinned.\n"
       "Tests: 71 unit nodes through the guarded runner in both flag states; 35-file comm set = the 5 accepted base failures; adversary r1 SOUND."),
 ),
 "R-CLIENT": dict(
  title="retro(mobile): R-CLIENT - logout lets an in-flight refresh land, refreshes an expired token once, and revokes the pair the server considers live (OTA-gated)",
  subject="retro(mobile): W1-4d logout awaits the in-flight refresh (5 s bound), refreshes an expired JWT once, and hands the rotated pair to the logout that owns the session",
  units="W1-4 client half (#140, merged in session 65b without review)",
  facts=("**CLIENT-ONLY, OTA-GATED:** phones on `97b5f15` are unaffected until the next `eas update --branch preview`. Backend halves (admin.sign_out regardless of refresh token, the expired-Bearer path) are R-AUTH.\n\n"
         "**Verdict:** adversary round 0 DEFECTIVE (major: the logout handoff slot accepted ANY epoch-guarded refresh from ANY session - user A's hung refresh could fill user B's logout) -> fix round (the handoff is keyed to the session epoch the logout ends; a refresh fills only the handoff whose epoch equals the epoch it was sent under; the cross-session scenario is pinned) -> adversary round 1 **SOUND** (2 minors recorded below).\n\n"
         "**Gates:** 103 tests across the 7 auth suites (w1-4d, w1-4, a3, api.refreshInterceptor, api.refreshMutex, ...) green; `tsc --noEmit` clean; eslint clean on the changed files; the FULL jest suite at commit time (summary appended below); `api.ts` adds exactly ONE read-only export `getInFlightRefresh()`; `/auth/logout` stays on the interceptor's skip-refresh list; the token is never logged.\n\n"
         "**Honest limits / follow-ups (adversary r1 minors):** (1) `epochAtRequest` is captured after refreshSession's SecureStore read, so a read that straddles a logout (the read itself hanging > 5 s across logout -> login(B) -> logout) can still hand A's pair to B's logout - follow-up PO-AUTH-W14D-01: capture the epoch before the read; (2) the handoff fill's `session?.access_token` term is unpinned (mutant A16: a 200 with an empty session would hand off `{access: undefined}` and skip the logout POST) - follow-up PO-AUTH-W14D-02: pin it.\n\n"
         "**CLAUDE.md correction carried by the next docs PR:** the W1-4 flag row's 'INERT until the client sends it' holds only until R-AUTH makes the backend call `admin.sign_out(access_token, \"local\")` regardless of the refresh token.\n"),
  msg=("Retro-fix group R-CLIENT for the W1-4 client half (#140). OTA-gated; phones on 97b5f15 unaffected.\n"
       "- logout() bumps the session epoch FIRST (P-A3), awaits an in-flight refresh bounded by 5 s, refreshes an EXPIRED\n  access token (JWT exp decoded without verification; malformed = expired-unknown = no refresh) exactly once, clears\n  the local session, then sends exactly ONE POST /auth/logout with the freshest pair held in memory; clearSession\n  stays in finally; every preparation error degrades to today's request.\n"
       "- refreshSession() hands a rotated pair that lands after the epoch bump to the logout whose handoff epoch equals\n  the epoch the refresh was sent under (never to a later session's logout); api.ts gains the read-only\n  getInFlightRefresh().\n"
       "Tests: 103 across 7 auth suites, tsc + eslint clean, full jest at commit time; adversary r1 SOUND (2 minors -> follow-ups)."),
 ),
}
EXTRA = SP / 'heads_extra.json'
if EXTRA.exists():
    HEAD.update(json.load(open(EXTRA, encoding='utf-8')))
HEAD = HEAD[KEY]

minors = [d for d in ADV.get("defects", []) if d.get("severity") == "minor"]
minor_lines = "".join(f"- {d.get('location','')[:140]}: {d.get('claim','')[:400]}\n" for d in minors)
head = (f"## Retro-fix {KEY} ({HEAD['units']})\n\n"
        "Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.\n\n"
        + HEAD["facts"]
        + (f"\n**Adversary round-1 minors, verbatim summary:**\n{minor_lines}" if minor_lines else "")
        + "\n---\n\n")
tail = "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
(SP / f"prbody_{KEY}.md").write_text(head + FIX["pr_text"].strip() + tail, encoding="utf-8", newline="\n")
(SP / f"msg_{KEY}.txt").write_text(HEAD["subject"] + "\n\n" + HEAD["msg"] + "\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n", encoding="utf-8", newline="\n")
(SP / f"title_{KEY}.txt").write_text(HEAD["title"], encoding="utf-8", newline="\n")
print(KEY, "body", len(head + FIX["pr_text"]), "msg ok")
