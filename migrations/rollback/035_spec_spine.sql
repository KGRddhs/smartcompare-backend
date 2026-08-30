-- Rollback 035: drop the spec_spine table
--
-- Safe by construction. Nothing reads this table unless BOTH
-- ENABLE_SPEC_SPINE is on AND SPEC_SPINE_TABLE names it; and even then a
-- missing table is not a crash — spec_spine_service._lookup_supabase_sync
-- swallows the error and falls back to the local data/spec_spine.json store,
-- which is where the spine lives by default anyway.
--
-- Correct order regardless: UNSET SPEC_SPINE_TABLE in Railway first, so no
-- in-flight lookup is aimed at a table that is about to disappear, then run
-- this. DROP is destructive — the seeded rows are gone. If the seed run cost
-- real completions, dump the table to data/spec_spine.json before dropping so
-- the work survives as the local store.

BEGIN;

DROP TABLE IF EXISTS public.spec_spine;

COMMIT;
