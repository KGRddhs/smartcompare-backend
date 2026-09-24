## Retro-fix R-MIG (W1-2 migration 037 (#153, merged in session 65 without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**MERGING THIS CHANGES NOTHING IN PRODUCTION** - 036/037/040 stay unapplied files. Apply order becomes `037 any time; 036 when its flag is readied (re-run 037 after a late 036); 040 any time; 038 = W3-16 (consent columns); 039 reserved for the M13-29 RLS migration`.

**Verdict:** adversary round 0 DEFECTIVE (major: 040's `proname` filter was unpinned - a mutant that revoked EVERY public function passed; two semantic mutants `PERFORM`/`pg_get_function_arguments` survived) -> fix round (source pins on the executed statement shape, the loop predicate, the 036 anon grant, the 037 header rule; docs lines corrected) -> adversary round 1 **SOUND** on a real engine (local throwaway PostgreSQL 18.1, Supabase-style default privileges): every round-0 mutant is killed.

**Gates:** 103 source-level unit nodes green (`tests/test_retro_w1_2b.py`, `_2c.py`, `_2d.py`, `tests/test_migration_037_security_definer_grants.py`, `tests/test_migration_index_predicate_immutability.py`); comm gate over the 25-file migration set base == head; the fix changed only comments in 037's executable SQL.

**Honest limits (adversary r1 minors, recorded, not blocking):** 040's `BEGIN;/COMMIT;` wrapper and the loop's WHERE are pinned only from below - `COMMIT->ROLLBACK`, an extra `AND p.pronargs = 0` or `AND false` conjunct survive the source pins (on the engine they leave anon EXECUTE standing with rc 0). The after-apply census in 040's header (the pg_proc/proacl query) is the real proof and MUST be run; a source test cannot replace it.

**CLAUDE.md / docs corrections carried by the next docs PR:** the migration apply-order sentence; `docs/CONTEXT_SESSION_LOG.md:68` still says `cleanup_expired_ratings` does not exist anywhere (it exists LIVE, created out of band - 040 revokes it by name); `docs/investigations/2026-09-11-w3-remainder-state.md:126` is corrected in this PR.

**Adversary round-1 minors, verbatim summary:**
- migrations/040_revoke_cleanup_expired_ratings.sql:73 and :100 (BEGIN; / COMMIT;); tests/test_retro_w1_2b.py (037 has test_pin_037_is_exactly: No test pins 040's transaction wrapper. Two mutants pass all 103 unit nodes: R1 changes COMMIT to ROLLBACK, and R1b deletes the COMMIT line. On local PG 18.1 (fresh throwaway cluster, 127.0.0.1:55443, Supabase-style fixture), each mutant ran under psql -f with ON_ERROR_STOP and gave rc 0 and the NOTICE '040: revoked EXECUTE on 2 public.cleanup_expired_ratings signature(s)'. Afterwards anon_x and a
- tests/test_retro_w1_2b.py::test_040_loop_is_filtered_to_exactly_cleanup_expired_ratings_in_public and ::test_040_revokes_cleanup_expired_rat: The new 040 pins bound the loop's WHERE only from below (no OR, LIKE or NOT) and count only `execute format(`. Several mutants therefore pass all 103 nodes:
- R4 adds `AND p.pronargs = 0`, a guessed signature. On the engine: rc 0 with NOTICE 'revoked EXECUTE on 1', and cleanup_expired_ratings(integer) still has anon_x=t and authd_x=t.
- R6 adds `EXIT;` after the first revoke. Same engine result: r

---

## R-MIG: fix the gaps in migration 037 (W1-2b/c/d), with a new migration 040 and a 036 amendment

**Nothing here changes production when it merges.** Migrations 035, 036, 037 and 040 are all unapplied. This PR changes no app code and adds no flag.

### Defects (retro adversary on PR #153, all reproduced)
1. **W1-2b: `cleanup_expired_ratings` was dismissed as nonexistent, but it exists live, out of band.**
   - `docs/investigations/2026-09-06-full-review-verified.json` records that an anon GET returned SQLSTATE 25006, so anon passed EXECUTE and the body ran.
   - 037 did nothing to it.
2. **W1-2c: 037 assumed CR-SECURITY-02 means "RLS is off".**
   - With RLS already on plus an out-of-band `USING (true)` policy, anon read 4 of 4 rows before 037 and 4 of 4 after.
   - The old rollback then DISABLEd RLS unconditionally, which let anon DELETE rows.
3. **W1-2d: 037 prescribed `035 -> 036 -> 037` as a hard prerequisite.**
   - On today's schema, statement 4 (036's function) made 037 fail with rc 3 and roll back entirely.

### Fixes
- **New `migrations/040_revoke_cleanup_expired_ratings.sql`.**
  - An idempotent DO block that loops `pg_proc` WHERE `n.nspname = 'public' AND p.proname = 'cleanup_expired_ratings'` and runs `EXECUTE format('REVOKE ALL ON FUNCTION public.%I(%s) FROM PUBLIC, anon, authenticated', proname, pg_get_function_identity_arguments(oid))`.
  - Revoke only: no GRANT (no repo caller exists), no CREATE, no DROP.
  - The header carries the pg_proc/proacl/pg_get_functiondef queries and the anon-executable SECURITY DEFINER census.
  - `rollback/040` contains comments only.
  - Numbering: 038 is W3-16's; 039 stays reserved for M13-29.
- **037 header.**
  - The `cleanup_expired_ratings` note is corrected and points to 040.
  - Added BEFORE checks for `user_events`: `pg_class relrowsecurity/relforcerowsecurity`, and `pg_policies` selecting `policyname, permissive, cmd, roles, qual, with_check`.
  - Added THE RULE. Each of these means 037 does NOT close CR-SECURITY-02:
    - RLS is already on;
    - any policy other than `events_insert`/`events_select` exists;
    - one of those two policies differs from how pg_policies renders 010:56-59 (a same-named `USING (true)`, for example).
- **037 statement 4** is wrapped in `IF to_regprocedure('public.home_savings_aggregate(uuid)') IS NOT NULL THEN ... END IF`. Statements 1-3 stay unguarded on purpose.
- **Apply order, everywhere it is written:** 037 any time; 036 whenever its flag is readied, then re-run 037; 035 is independent. This covers the 037 header, the next-units doc and the w3-remainder-state doc.
- **036:** the revoke is now `FROM PUBLIC, anon`.
- **rollback/037:** restores the RECORDED BEFORE `relrowsecurity`. The value ships as NULL, and NULL raises, so nothing changes. `true` leaves RLS on, and only `false` DISABLEs.

### Fix-phase hardening (retro adversary on the green, all four defects reproduced on a local PG 18.1 and fixed)
- **040's name filter was unpinned (major).**
  - Deleting `AND p.proname = ...` revoked EXECUTE from anon and authenticated on EVERY public function (resolve_referral_code included), with rc 0 and a NOTICE that still claimed it had revoked cleanup_expired_ratings.
  - New pin: the loop's WHERE must be a pure AND of equalities containing `proname = 'cleanup_expired_ratings'` and a public-schema restriction.
  - This kills the drop-filter, `LIKE 'cleanup%'`, `OR` and drop-schema mutants. The main file's census pin now also requires the executable filter.
- **Two more 040 mutants were unpinned.**
  - `PERFORM format(` builds the REVOKE and never runs it, while still printing a success NOTICE. The roles are now read from the literal that `EXECUTE format(` runs.
  - `pg_get_function_arguments` gives rc 3 on a DEFAULT overload. A new pin requires the identity signature, fed from the loop record.
- **Apply order was still wrong in docs.** `docs/investigations/2026-09-11-w3-remainder-state.md:126` still said `035 -> 036 -> 037`; it is corrected, and a new pin scans every investigations doc.
- **THE RULE keyed on names only.** RLS off plus a same-named `events_select USING (true)` gave anon 4 -> 4 after 037. The header now prints the expected pg_policies rendering and states that any difference means NOT closed, and this is pinned.
- **Tests that proved nothing, now real pins.**
  - The statement-4 guard must be the WHOLE IF condition, which kills `IS NOT NULL AND false` and `OR true`.
  - 036's GRANT must be exactly {authenticated, service_role}, and no migration or rollback may grant home_savings_aggregate to anon or PUBLIC. This kills the "add anon to 036's GRANT" mutant, which matters in the late-036 order.
- **sqlfluff size limit.** The first draft of this fix pushed 037 past sqlfluff 4.3.0's 20000-byte `large_file_skip_byte_limit`, and lint then silently SKIPPED it with exit 0. The header was tightened (19879 B CRLF / 19557 B LF), and a size pin now guards it.

### Flag row
None. There is no runtime code. 037's executable SQL is identical to the green's; the fix phase changed comments only.

### Evidence
- **Unit files:** 103 passed, 0 failed.
- **Comm gate:** HEAD 519 passed / 0 failed over 28 files; base 474/0 at 1c6f6796; branch-only new failures: none.
- **Mutation:** 19 fix-phase mutants, all killed, with sha-verified restores. The green's earlier 31 were all killed too.
- **Lint:** ruff, compile and `sqlfluff lint migrations/` are clean, with nothing skipped.
- **Local PostgreSQL 18.1** with Supabase-style roles and default privileges:
  - 037 applies with rc 0 without 036;
  - 040 gives rc 0 with the function absent, present and with overloads, and on re-run;
  - after both, anon holds EXECUTE only on resolve_referral_code and unrelated functions;
  - the header's pg_policies query flags the same-named `USING(true)` case.

### Activation gate (Ahmed, in order)
1. Before 037, run and keep the `pg_class` and `pg_policies` output. Compare both expected policies column by column against the rendering printed in the header.
2. Before 040, run 040's header queries.
3. Apply 037 and 040, in either order.
4. After apply:
   - proacl on `delete_user_cascade`/`increment_lifetime_comparisons` has no `anon=`, `authenticated=` or bare `=X` entry;
   - the anon-key `rpc/delete_user_cascade` POST returns 42501;
   - an anon `count=exact` on `user_events` returns 0;
   - an anon GET on `rpc/cleanup_expired_ratings` never again returns 25006;
   - the census lists only `resolve_referral_code`.
5. If the BEFORE checks showed RLS already on, an extra policy or a changed definition, CR-SECURITY-02 stays OPEN until a follow-up migration fixes those policies by name.
6. If 036 is applied after 037, re-run 037.

### Context-file corrections (separate docs PR; not edited here)
- **CLAUDE.md:370** (`ENABLE_SYNC_DB_OFFLOAD` row): "the behaviour-profile RPC (needs migration 037)" -> "needs a future migration (unnumbered)".
- **CLAUDE.md, SESSION 65c ADDENDUM, #153 bullet:** "apply order `035 -> 036 -> 037`" -> "037 applies any time (statement 4 is guarded by `to_regprocedure('public.home_savings_aggregate(uuid)')`); 036 whenever `ENABLE_HOME_SAVINGS_AGGREGATE` is readied, then re-run 037; 035 independent; run 037's `user_events` BEFORE checks first; apply 040 for `cleanup_expired_ratings`."
- **CLAUDE.md, SESSION 65 "Corrections to the consolidated review itself":** "`cleanup_expired_ratings` ... does not exist anywhere in migrations/ or app/" -> "exists LIVE, out of band (anon GET -> SQLSTATE 25006, recorded in docs/investigations/2026-09-06-full-review-verified.json); it is in no migration, which is why a repo grep misses it; migration 040 revokes it from PUBLIC, anon, authenticated."
- **docs/CONTEXT_SESSION_LOG.md:68**, "(6) Corrections to the consolidated review itself": "`cleanup_expired_ratings` ... does not exist anywhere" -> the same sentence as the CLAUDE.md SESSION 65 correction above.

### Honest limits
- The real signature, body and ACL of `cleanup_expired_ratings` are unknown; the local test used stand-ins.
- Where service_role has no explicit default grant, 040 also removes its EXECUTE (no repo caller exists).
- The rollback needs the recorded BEFORE value.
- All engine evidence comes from a local PostgreSQL emulation, not Supabase: no PostgREST and no schema cache.

### Follow-ups
- **W1-2e:** fold the order-aware census pins from `tests/test_retro_w1_2d.py` into the main 037 test file.
- A policy-repair migration if the BEFORE output demands one.
- FORCE ROW LEVEL SECURITY is still undecided.
- Next-units doc lines 58 and 142 still say "033-036 unapplied".
- rollback/037's stale "no PostgreSQL on the machine" line.
- The CLAUDE.md and CONTEXT_SESSION_LOG corrections above.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
