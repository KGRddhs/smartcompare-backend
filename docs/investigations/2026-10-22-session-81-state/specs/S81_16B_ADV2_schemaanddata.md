# S81-16b KB-BRANDS adversary report: schema-and-data lens (Opus 5.5, 2026-11-04)

Verdict: SOUND (no blocking, no major; 6 minors = stated-limit / documentation candidates, LC-4).
Staged with the Write tool (a Bash command over ~7 KB is rejected on this box), then copied into place and byte-checked by python through the shell.

## Identity
- Worktree sc-s81-s16b HEAD 28eec42b2055920604acb1e4ef9765fe74126625 (verified first and last); git status clean; junction untouched.
- Frozen RED file tests/test_s81_s16b_kb_brands.py cd67db3bd75d90ae90eeb90ce48c90aac4bb9131ac8e99753e99b36738b75cbd first and last (worktree and scratch copy).
- Scratch worktree S81-16b_adv_schemaanddata (detached at 28eec42b) made, then removed with `git worktree remove --force` (verified gone). Its autocrlf checkout wrote CRLF migrations; the four migration files were re-written from the commit blobs and sha-verified equal to GREEN's (052 fef8ec19..., rollback 766cff1c...) before any probe. A per-worktree core.autocrlf=false went with the worktree (the repo already had extensions.worktreeConfig; the shared config is unchanged).

## Runs ([pyt] lines; one pytest at a time; waited ~20 min for another lane's comm chunks; nothing killed)
- RED file + the seven migration readers on the exact bytes: 297 passed (129 + 168). `[pyt] tag=s16b-advsd-schema start=2026-11-04 23:39:11 end=2026-11-04 23:39:49 elapsed=38s bound=600s status=OK rc=0`
- sqlfluff lint --config .sqlfluff on 052 + rollback + the three APPLY_052 files: All Finished, no violation. Neither 052 file contains '051'. Both 052 files: 0 bytes > 127, 0 CR, end in LF.

## Mutants of this lens (byte copies, restored and sha-verified after each; 10 / 10 KILLED)
SD1 REVOKE omits service_role -> b05 | SD2 SQL deny belt dropped -> b03 | SD3 host index UNIQUE -> b07 | SD4 label_ar btrim dropped -> b03 | SD5 extra GRANT SELECT to anon -> b05 | SD6 builder skips kb_source_allowed -> k03[host-rule-only] | SD7 builder host cap 254 -> k03[host-254] | SD8 RLS line removed -> b05 | SD9 human exclusion dropped from the SPARQL -> s03 | SD10 writer update drops the source filter -> s05[none-returned].
Tags s16b-advsd-SD1..SD10 (5-13 s each, status=FAIL rc=1 = killed); logs + table: S81-16b_adv/sad_logs/ (mutants.txt).

## Own throwaway PostgreSQL 18.1 cluster (S81-16b_adv/sad_pg/, port 55443, initdb -E UTF8 --locale=C; stopped; data directory left, no recursive delete)
Transcript: S81-16b_adv/sad_pg/probes_db.txt; matrix: k03_matrix.py, k03.sql, k03_db.out, k03_builder.json, k03_cmp.py.
1. K03 re-derived from the SQL text, MEASURED: 103 cases (15 qids incl. Q0 / Q01 / q1 / trailing newline / Arabic-Indic and fullwidth digits / 13 digits; 24 label shapes on both label_en and label_ar incl. 128 / 129 code points in ASCII, Arabic, e-acute, astral emoji, combining marks, every whitespace kind at either end, NUL, lone surrogate; 35 hosts incl. 253 / 254 chars, IDN raw and punycode, IPv4, 0x-hex top label, digit registrable labels 4711.com / 163.com, every deny name, trailing dot, port, scheme, underscore; 5 sources). Each case: builder verdict vs a real INSERT under BEGIN / ROLLBACK. Result: 85 agree, 0 builder-accepts-DB-refuses, 14 DB-accepts-builder-refuses = exactly the GC-4 Q3 strip superset (tab, newline, NBSP, ideographic space, 0x1c, NEL at either end); 4 NUL / surrogate cases builder-refused (PostgreSQL cannot store them). The builder never hands the database a row 052 refuses.
2. 052 without 045 (fresh database): the DO guard raises, the transaction rolls back, kb_brands absent.
3. Supabase-shaped default privileges (ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES / FUNCTIONS TO anon, authenticated, service_role, before 045 + 052): the POSTCHECK grid comes out exactly as the file states (check_count 6, every anon / authenticated column f, sr_truncate f, row_count 0); REFERENCES / TRIGGER / MAINTAIN false for all three roles; relacl = owner + service_role=arwd only. kb_set_updated_at EXECUTE stays service_role-only (052 widens nothing).
4. Writer emulation as service_role with BYPASSRLS (the Supabase attribute): an 'operator' row is skipped by the insert-ignore and the filtered UPDATE ... WHERE qid AND source = 'wikidata' changes 0 rows; RETURNING returns only the newly inserted qid. A duplicate qid inside ONE insert-ignore statement: the first wins, no 21000 error.
5. anon INSERT / DELETE / TRUNCATE: permission denied.
6. Rollback order with rows present: the 045 rollback first fails 2BP01 and changes nothing (3 rows kept); rollback 052 then 045 clean, 0 kb_ tables left.

## Checklist of the lens
- 037 both-readings rule + 045 pattern: RLS on, no policy; REVOKE ALL FROM PUBLIC, anon, authenticated, service_role; then GRANT SELECT, INSERT, UPDATE, DELETE TO service_role; no anon / PUBLIC grant; the same form as 045 lines 484-517. OK.
- Rollback: DROP TABLE IF EXISTS only; the 045 function is kept; the header names the 052-before-045 order; the 045 rollback has no CASCADE, so the wrong order fails closed (measured by GREEN G9 and here). OK.
- Every CHECK mirrored: qid (the leaf's _sql_match turns $ into \Z, so no trailing-newline gap), labels 1..128 + btrim (builder stricter), official_host length + KB_HOST_REGEX + deny belt + top-label constraint (+ kb_source_allowed, stricter), source enum, NOT NULLs; measured above. OK.
- Trigger: BEFORE UPDATE on the 045 SECURITY INVOKER function; G9 and probe 4 show it moving updated_at. Partial index WHERE official_host IS NOT NULL, not unique. OK.
- APPLY_052 grids vs the final bytes: ONE_PASTE = a 3-line header + migrations/052_kb_brands.sql byte for byte (diff measured); PRECHECK and POSTCHECK grids reproduced on a plain cluster (GREEN G9) and on a Supabase-defaults cluster (here). OK.
- G9 transcript (GREEN): read in full; consistent with the bytes; the service_role 0-row SELECT (D6) is the no-BYPASSRLS plain cluster, confirmed by probe 4 with BYPASSRLS.
- CC0: stated in the 052 header, the table COMMENT, the script docstring, CLAUDE.md and the PR body. OK.
- No personal data: no user / device / session / address column, no FK; the 043 fence (B08 + test_migration_043) green; the human exclusion FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . } present and pinned (SD9 killed). OK, with m1.
- L6 beside 'MERGING THIS CHANGES NOTHING IN PRODUCTION' in the PR body, with owner step 0. OK.
- No migration manifest outside migrations/ needs 052 (git grep of the 045 / 050 file names: CLAUDE.md and tests only).

## Blocking
None.

## Major
None.

## Minor (stated limits / documentation, LC-4)
- m1 The 052 header says a label is "never a person's name". The P31 Q5 filter excludes items that ARE humans; many brand items carry their founder's name (a public trade name). Reword to "never the label of a human item", or state it as a limit. No data defect.
- m2 L4 does not name Wikidata item merges: when an item is merged into another (a redirect), the old qid row stays and the surviving qid is inserted beside it, so one brand can hold two rows until an operator removes one. Add to L4.
- m3 Owner canary step 6 (`updated_at > created_at` after a second run) is a weak proof: created_at is the database now() at insert while updated_at is the script host's now() at derive time (the 045 builder pattern), so a host clock ahead of the database clock makes fresh inserts pass too. Stronger: max(updated_at) later than the second run's start time. Fresh rows normally have updated_at slightly earlier than created_at (as in every 045 table).
- m4 Interior control characters in a label (a newline inside, C0 controls) pass both the CHECK and the builder (only the ends are trimmed). Stated limit for the serving unit: escape labels on render.
- m5 POSTCHECK counts the CHECK constraints (6) but does not compare their text; a stale pre-existing table would pass, which PRECHECK kb_brands_absent = true already guards. Its ::regclass casts raise rather than return false when the table is missing (step 3 only runs after step 2).
- m6 POSTCHECK does not list REFERENCES / TRIGGER / MAINTAIN for anon / authenticated; measured false here under Supabase default privileges. Informational.

## Not measured
- The PostgREST half of L7 (offline); the real Wikidata answer (L1); the Supabase server itself (simulated: default privileges + BYPASSRLS on PostgreSQL 18.1; Supabase runs 15 / 17, which have no contype 'n' rows, so check_count 6 holds there too).
